import sys
import os
import requests
import xml.etree.ElementTree as ET
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import time

try:
    from google import genai
except ImportError:
    print("Warning: google-genai not installed. Please 'pip install google-genai'")
    genai = None

try:
    from pyzotero import zotero
except ImportError:
    print("Warning: pyzotero not installed. Please 'pip install pyzotero'")
    zotero = None

# Ensure stdio uses utf-8 to handle special characters from PubMed
sys.stdout.reconfigure(encoding='utf-8')

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuration variables
PUBMED_API_KEY = os.getenv("PUBMED_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Zotero Configuration
ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_USER_ID = os.getenv("ZOTERO_USER_ID")
ZOTERO_COLLECTION_ID = os.getenv("ZOTERO_COLLECTION_ID")

# Email Configuration
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

# Construct the query components
CORE_QUERY = '(COPD OR "chronic obstructive pulmonary disease" OR asthma OR bronchiectasis OR IPF OR "Pulmonary fibrosis" OR "smoking cessation" OR "Catheter-related bloodstream infection" OR CRBSI OR "catheter-associated urinary tract infection" OR CAUTI OR "ventilator-associated pneumonia" OR VAP OR "osteoinductive factor" OR BICRI OR REVOCART OR minocycline OR fluzole OR "bronchiolitis obliterans" OR "lung transplantation" OR "chronic cough" OR mepolizumab OR pirfenidone OR dupilumab OR benralizumab)'
STUDY_TYPE_FILTER = 'AND (Randomized Controlled Trial[PT] OR Meta-Analysis[PT] OR Systematic Review[PT])'
NEGATIVE_FILTER = 'NOT (pediatric OR child OR children OR infants OR neonatal)'

# Combine into a single comprehensive query
FULL_QUERY = f"{CORE_QUERY} {STUDY_TYPE_FILTER} {NEGATIVE_FILTER}"

client = None
if genai and GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize Zotero instance
zot = None
if zotero:
    try:
        zot = zotero.Zotero(ZOTERO_USER_ID, 'user', ZOTERO_API_KEY)
    except Exception as e:
        print(f"Error initializing Zotero: {e}")

def ingest_to_zotero(title, abstract, url, pmid, authors, journal, journal_abbr, date, doi, volume, issue, pages):
    """Branch A: Sterile Zotero Ingestion using official NCBI metadata."""
    if not zot:
        print(f"[Zotero] Pyzotero not installed or configured. Skipping PMID: {pmid}")
        return False
        
    try:
        template = zot.item_template('journalArticle')
        template['title'] = title
        template['abstractNote'] = abstract
        template['url'] = url
        template['extra'] = f"PMID: {pmid}"
        if journal: template['publicationTitle'] = journal
        if journal_abbr: template['journalAbbreviation'] = journal_abbr
        if date: template['date'] = date
        if doi: template['DOI'] = doi
        if volume: template['volume'] = volume
        if issue: template['issue'] = issue
        if pages: template['pages'] = pages
        
        zotero_creators = []
        for author in authors:
            if author.get('last') or author.get('first'):
                zotero_creators.append({
                    'creatorType': 'author',
                    'firstName': author.get('first', ''),
                    'lastName': author.get('last', '')
                })
        if zotero_creators:
            template['creators'] = zotero_creators
        
        # Add to the specific collection
        template['collections'] = [ZOTERO_COLLECTION_ID]
        
        resp = zot.create_items([template])
        if resp and resp.get('successful'):
            print(f"[Zotero] Successfully ingested PMID: {pmid}")
            return True
        else:
            print(f"[Zotero] Failed to ingest PMID: {pmid}. Response: {resp}")
            return False
    except Exception as e:
        print(f"[Zotero] Exception during ingestion for PMID: {pmid} - {e}")
        return False

def analyze_with_gemini(title, abstract):
    """Branch B: Gemini AI Analysis for Email Report."""
    if not genai or not GEMINI_API_KEY:
        return {
            "Research Method": "Unclear (Gemini API Config Missing)",
            "n-Value": "Unclear (Gemini API Config Missing)",
            "Abstract Summary": "Unclear (Gemini API Config Missing)",
            "Impact & Evidence Rating": "Unclear (Gemini API Config Missing)"
        }
    
    prompt = f"""
Please analyze the following scientific abstract and extract the required information for a high-fidelity clinical synthesis.
Prioritize accuracy over fluency. If information for any field is ambiguous or not explicitly stated, mark it as 'Unclear' rather than generating speculative data.

Please output your response STRICTLY as a JSON object with the exact following string keys:
"Research Method" : [Formal Full English Term] ([Traditional Chinese Annotation]). Constraint: Use formal full terms (e.g. Randomized Controlled Trial, NOT RCT). The Chinese annotation must be strictly under 30 chars. Logic Guard: If ambiguous, use the most specific full-length English term and set the annotation to "待進一步臨床核實". e.g. "Randomized Controlled Trial (雙盲隨機對照試驗，評估 Minocycline 對於 VAP 之療效)"
"n-Value" : Traditional Chinese only. Summarize the sample size, cohort composition, or population details. Constraint: Total length must be strictly under 30 characters. e.g. "共 450 名加護病房使用呼吸器之成年患者"
"Abstract Summary" : Chinese (Traditional) abstract summary under 100 characters
"Impact & Evidence Rating" : Chinese (Traditional) assessment of impact and evidence rating

Title: {title}
Abstract: {abstract}
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        text = response.text.strip()
        
        # Clean potential markdown wrappers
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        result = json.loads(text)
        return {
            "Research Method": result.get("Research Method", "Unclear"),
            "n-Value": result.get("n-Value", "Unclear"),
            "Abstract Summary": result.get("Abstract Summary", "Unclear"),
            "Impact & Evidence Rating": result.get("Impact & Evidence Rating", "Unclear")
        }
    except Exception as e:
        print(f"Error during Gemini analysis: {e}")
        return {
            "Research Method": "Error",
            "n-Value": "Error",
            "Abstract Summary": "Error",
            "Impact & Evidence Rating": "Error"
        }

def search_pubmed():
    """Search PubMed and retrieve a list of PMIDs matching the criteria from the last 24 hours."""
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    
    # Search 1: by EDAT (articles newly entered into PubMed)
    params_edat = {
        "db": "pubmed",
        "term": FULL_QUERY,
        "reldate": 1,
        "datetype": "edat",
        "retmode": "json",
        "api_key": PUBMED_API_KEY,
        "retmax": 100
    }

    # Search 2: by MHDA (articles that completed MeSH indexing today)
    params_mhda = {
        "db": "pubmed",
        "term": FULL_QUERY,
        "reldate": 1,
        "datetype": "mhda",
        "retmode": "json",
        "api_key": PUBMED_API_KEY,
        "retmax": 100
    }
    
    try:
        response_edat = requests.get(search_url, params=params_edat)
        response_edat.raise_for_status()
        data_edat = response_edat.json()
        pmids_from_edat = data_edat.get("esearchresult", {}).get("idlist", [])
        
        response_mhda = requests.get(search_url, params=params_mhda)
        response_mhda.raise_for_status()
        data_mhda = response_mhda.json()
        pmids_from_mhda = data_mhda.get("esearchresult", {}).get("idlist", [])
        
        # Merge results and remove duplicates by PMID
        all_pmids = list(set(pmids_from_edat + pmids_from_mhda))
        return all_pmids
    except Exception as e:
        print(f"Error searching PubMed: {e}")
        return []

def fetch_details(id_list):
    """Fetch structured metadata and abstracts for a list of PMIDs."""
    if not id_list:
        return []
        
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "xml",
        "api_key": PUBMED_API_KEY
    }
    
    try:
        response = requests.get(fetch_url, params=params)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        results = []
        
        for article in root.findall(".//PubmedArticle"):
            pmid_node = article.find(".//PMID")
            pmid = pmid_node.text if pmid_node is not None else "Unknown PMID"
            
            article_node = article.find(".//Article")
            title = article_node.findtext("ArticleTitle") if article_node is not None else "No Title"
            
            abstract_nodes = article.findall(".//AbstractText")
            if abstract_nodes:
                abstract = " ".join([node.text for node in abstract_nodes if node.text])
            else:
                abstract = "No abstract available."
                
            journal = article.findtext(".//Journal/Title") or ""
            journal_abbr = article.findtext(".//Journal/ISOAbbreviation") or article.findtext(".//MedlineJournalInfo/MedlineTA") or ""
            
            # Advanced date parsing for full YYYY-MM-DD format
            date_str = ""
            artdate = article.find('.//ArticleDate')
            pubdate = article.find('.//PubDate')
            
            if artdate is not None:
                y = artdate.findtext('Year') or ""
                m = artdate.findtext('Month') or ""
                d = artdate.findtext('Day') or ""
                if y:
                    date_str = y
                    if m: date_str += f"-{m.zfill(2)}"
                    if d: date_str += f"-{d.zfill(2)}"
            
            if not date_str and pubdate is not None:
                y = pubdate.findtext('Year') or ""
                m = pubdate.findtext('Month') or ""
                d = pubdate.findtext('Day') or ""
                if y:
                    date_parts = [p for p in (y, m, d) if p]
                    date_str = " ".join(date_parts)
                    
            authors = []
            for author in article.findall(".//Author"):
                last = author.findtext("LastName") or ""
                first = author.findtext("ForeName") or ""
                authors.append({"first": first, "last": last})
                
            doi = article.findtext('.//ArticleId[@IdType="doi"]') or ""
            volume = article.findtext('.//JournalIssue/Volume') or ""
            issue = article.findtext('.//JournalIssue/Issue') or ""
            pages = article.findtext('.//Pagination/MedlinePgn') or ""
                
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            
            # --- PARALLEL ARCHITECTURE START ---
            
            # Branch A: Sterile Zotero Ingestion (Source of Truth)
            ingest_to_zotero(title, abstract, url, pmid, authors, journal, journal_abbr, date_str, doi, volume, issue, pages)
            
            # Branch B: Gemini AI Analysis (Clinical Assistant)
            ai_data = analyze_with_gemini(title, abstract)
            
            # --- PARALLEL ARCHITECTURE END ---
            
            time.sleep(2) # Prevent potential rate limiting from free tier
            
            results.append({
                "PMID": pmid,
                "Title": title,
                "URL": url,
                "Abstract": abstract,
                "Research Method": ai_data["Research Method"],
                "n-Value": ai_data["n-Value"],
                "Abstract Summary": ai_data["Abstract Summary"],
                "Impact & Evidence Rating": ai_data["Impact & Evidence Rating"]
            })
            
        return results
    except Exception as e:
        print(f"Error fetching/parsing details from PubMed: {e}")
        return []

def send_email(subject, html_content):
    try:
        print("\nSending email...")
        receivers = [r.strip() for r in RECEIVER_EMAIL.split(",")]
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(receivers)
        msg['Subject'] = subject
        
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        for receiver in receivers:
            server.sendmail(SENDER_EMAIL, receiver, msg.as_string())
        server.quit()
        print(f"Email successfully sent to {RECEIVER_EMAIL}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    print("Initiating daily PubMed query...")
    print(f"Query string: {FULL_QUERY}")
    
    pmids = search_pubmed()
    today_str = datetime.now().strftime('%Y-%m-%d')
    date_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not pmids:
        print("\nNo articles found matching the criteria in the last 24 hours.")
        subject = f"[Future Lab] System Alert: No results found today."
        email_content = f'''
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>No results found today.</h2>
            <p>Generated on: {date_time_str}</p>
            <hr>
            <p>There were no new PubMed articles matching the specified criteria in the last 24 hours.</p>
        </body>
        </html>
        '''
        send_email(subject, email_content)
        return

    print(f"\nFound {len(pmids)} new articles in the last 24 hours. Fetching details and analyzing...\n")
    articles = fetch_details(pmids)
    
    subject = f"[Future Lab] PubMed Daily Report - {today_str}"
    
    email_content = f'''
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .article {{ border-bottom: 1px solid #ccc; padding-bottom: 20px; margin-bottom: 20px; }}
            .title {{ font-size: 18px; font-weight: bold; color: #2c3e50; }}
            .metadata {{ font-size: 14px; margin-bottom: 10px; }}
            .ai-summary {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; }}
        </style>
    </head>
    <body>
        <h2>Daily PubMed Summary</h2>
        <p>Generated on: {date_time_str}</p>
        <hr>
    '''
    
    for i, article in enumerate(articles, 1):
        # Print to console for local logging
        print(f"[{i}] {article['Title']}")
        print(f"    PMID: {article['PMID']} | URL: {article['URL']}")
        print(f"    Method: {article['Research Method']} | n-Value: {article['n-Value']}")
        print(f"    Summary (ZH): {article['Abstract Summary']}")
        print(f"    Impact (ZH): {article['Impact & Evidence Rating']}")
        print("-" * 80)
        
        # Add to HTML email
        email_content += f'''
        <div class="article">
            <div class="title">{i}. {article['Title']}</div>
            <div class="metadata">
                <b>PMID:</b> {article['PMID']} | <b>Link:</b> <a href="{article['URL']}">{article['URL']}</a><br>
                <b>Research Method:</b> {article['Research Method']}<br>
                <b>n-Value:</b> {article['n-Value']}
            </div>
            <div class="ai-summary">
                <b>Abstract Summary (摘要):</b><br>
                {article['Abstract Summary']}<br><br>
                <b>Impact & Evidence Rating (影響力與證據等級):</b><br>
                {article['Impact & Evidence Rating']}
            </div>
        </div>
        '''
        
    email_content += "</body></html>"
    
    send_email(subject, email_content)

if __name__ == "__main__":
    main()
