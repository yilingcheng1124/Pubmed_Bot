import sys
import os
import requests
import xml.etree.ElementTree as ET
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import yaml
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
with open('config/settings.yaml', 'r', encoding='utf-8') as f:
    settings = yaml.safe_load(f)

CORE_QUERY = settings['query']['core']
STUDY_TYPE_FILTER = settings['query']['study_type_filter']
NEGATIVE_FILTER = settings['query']['negative_filter']

# Date axis for the daily search window.
# NOTE: The query filters on Publication Type ([PT]) and MeSH ([MH]) tags, which are
# only assigned when an article completes MeSH indexing -- typically days to weeks AFTER
# it first enters PubMed. Searching by 'edat' (entry date) therefore matches brand-new,
# un-indexed records that lack those tags, yielding ~0 results every day. 'mhda' (MeSH
# date) aligns the window with when those tags are actually applied.
_search_cfg = settings.get('search', {}) or {}
_dt = _search_cfg.get('datetype', 'mhda')
SEARCH_DATETYPE = _dt[0] if isinstance(_dt, list) and _dt else (_dt if isinstance(_dt, str) else 'mhda')

GEMINI_MODEL = settings['report']['gemini_model']
EMAIL_SUBJECT_PREFIX = settings['report']['email_subject_prefix']
REPORT_LANGUAGE = settings['report']['language']

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
"Research Method" : [Formal Full English Term] ([{REPORT_LANGUAGE} Annotation]). Constraint: Use formal full terms (e.g. Randomized Controlled Trial, NOT RCT). The annotation must be strictly under 30 chars and written in {REPORT_LANGUAGE}. Logic Guard: If ambiguous, use the most specific full-length English term and set the annotation to "待進一步臨床核實" if language is zh-TW, or "Pending further clinical verification" if language is en. e.g. "Randomized Controlled Trial (雙盲隨機對照試驗，評估 Minocycline 對於 VAP 之療效)"
"n-Value" : {REPORT_LANGUAGE} only. Summarize the sample size, cohort composition, or population details. Constraint: Total length must be strictly under 30 characters. e.g. "共 450 名加護病房使用呼吸器之成年患者"
"Abstract Summary" : A detailed and comprehensive {REPORT_LANGUAGE} summary capturing the study's background, key results, and conclusion. Do not be overly brief; aim for a length between 300 and 500 characters.
"Impact & Evidence Rating" : {REPORT_LANGUAGE} assessment of impact and evidence rating

Title: {title}
Abstract: {abstract}
"""
    max_retries = 6
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
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
            error_str = str(e).upper()
            if "429" in error_str or "503" in error_str or "RESOURCE_EXHAUSTED" in error_str or "UNAVAILABLE" in error_str or "TIMEOUT" in error_str:
                if attempt < max_retries - 1:
                    wait_time = 15 * (2 ** attempt)
                    print(f"API error (attempt {attempt + 1} of {max_retries}): {e}. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
            print(f"Error during Gemini analysis: {e}")
            return {
                "Research Method": "Error",
                "n-Value": "Error",
                "Abstract Summary": "Error",
                "Impact & Evidence Rating": "Error"
            }

def search_pubmed():
    """Search PubMed and retrieve a list of PMIDs matching the criteria from yesterday."""
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')

    # Search by MeSH date so the window matches when [PT]/[MH] tags are applied (see SEARCH_DATETYPE note)
    params = {
        "db": "pubmed",
        "term": FULL_QUERY,
        "mindate": yesterday,
        "maxdate": yesterday,
        "datetype": SEARCH_DATETYPE,
        "retmode": "json",
        "api_key": PUBMED_API_KEY,
        "retmax": 100
    }

    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()
        pmids = data.get("esearchresult", {}).get("idlist", [])

        # Remove duplicates by PMID just in case
        all_pmids = list(set(pmids))
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
            
            time.sleep(13) # Prevent potential rate limiting from free tier
            
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
        subject = f"{EMAIL_SUBJECT_PREFIX} System Alert: No results found today."
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
    
    subject = f"{EMAIL_SUBJECT_PREFIX} PubMed Daily Report - {today_str}"
    
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
