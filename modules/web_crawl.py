import json
import requests
import trafilatura
from urllib.parse import urlparse

def extract_with_trafilatura(url):
    
    blocklist = ["facebook.com", "youtube.com", "instagram.com", "twitter.com", "x.com"]
    if any(domain in url for domain in blocklist):
        return {
            "title": "Skipped", 
            "text": "Skipped: Unsupported domain",
            "extraction_method": "skipped",
            "content_length": 0
        }
    
    try:
        downloaded = trafilatura.fetch_url(url)
        
        if not downloaded:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            downloaded = response.text
        
        if not downloaded:
            return {
                "title": "Error", 
                "text": "Failed to download content with both methods",
                "extraction_method": "failed",
                "content_length": 0
            }
        
        extracted = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            favor_recall=True
        )
        
        title = "Untitled"
        try:
            metadata = trafilatura.extract_metadata(downloaded)
            if metadata:
                if hasattr(metadata, 'title') and metadata.title:
                    title = metadata.title
                elif isinstance(metadata, dict) and metadata.get("title"):
                    title = metadata["title"]
                elif hasattr(metadata, '__dict__') and hasattr(metadata, 'title'):
                    title = getattr(metadata, 'title', 'Untitled')
        except Exception:
            title = "Untitled"
        
        if extracted and len(extracted.strip()) > 50:
            return {
                "title": title,
                "text": extracted.strip(),
                "extraction_method": "trafilatura",
                "content_length": len(extracted.strip())
            }
        else:
            return {
                "title": title,
                "text": f"Content too short or not found (trafilatura extracted: {len(extracted) if extracted else 0} chars)",
                "extraction_method": "failed",
                "content_length": 0
            }

    except Exception as e:
        return {
            "title": "Error", 
            "text": f"Error extracting: {str(e)}",
            "extraction_method": "failed",
            "content_length": 0
        }

def load_input_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_to_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def crawl_and_extract(url_list):
    results = []
    
    for entry in url_list:
        url = entry.get("link", "")

        result = extract_with_trafilatura(url)
        
        domain = entry.get("domain", "")
        if not domain:
            try:
                domain = urlparse(url).netloc
            except:
                domain = "unknown"
        
        results.append({
            "domain": domain,
            "link": url,
            "title": result["title"],
            "content": result["text"],
            "extraction_method": result.get("extraction_method", "unknown"),
            "content_length": result.get("content_length", 0)
        })
    
    return results

def main():
    INPUT_FILE = "data/organic_pairs.json"
    OUTPUT_FILE = "data/output.json"
    
    url_list = load_input_json(INPUT_FILE)
    if not url_list:
        return
    
    output_data = crawl_and_extract(url_list)
    save_to_json(output_data, OUTPUT_FILE)
    print(f"Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()