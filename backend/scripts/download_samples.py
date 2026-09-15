import urllib.request
import os

def download_samples():
    base_url = "https://raw.githubusercontent.com/LennysNewsletter/lennys-newsletterpodcastdata/main/data/podcast_transcripts/"
    # We will fetch a couple of sample transcripts from the public repo
    samples = [
        "148_Brian_Chesky_on_what_to_do_when_product_management_is_no.md",
        "154_Linear’s_growth_engine_nanNan_Oki_Head_of_Growth_.md"
    ]
    
    target_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "transcripts")
    os.makedirs(target_dir, exist_ok=True)
    
    for sample in samples:
        url = base_url + sample
        target_path = os.path.join(target_dir, sample)
        print(f"Downloading {sample}...")
        try:
            urllib.request.urlretrieve(url, target_path)
            print(f"Saved to {target_path}")
        except Exception as e:
            print(f"Failed to download {sample}: {e}")

if __name__ == "__main__":
    download_samples()
