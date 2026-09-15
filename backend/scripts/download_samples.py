import os
import urllib.request

# Selected podcast transcripts from the legitimate lennys-newsletterpodcastdata repository
TRANSCRIPTS = [
    "https://raw.githubusercontent.com/LennysNewsletter/lennys-newsletterpodcastdata/main/podcasts/brian-halligan.md",
    "https://raw.githubusercontent.com/LennysNewsletter/lennys-newsletterpodcastdata/main/podcasts/evan-spiegel.md",
    "https://raw.githubusercontent.com/LennysNewsletter/lennys-newsletterpodcastdata/main/podcasts/tony-fadell.md",
    "https://raw.githubusercontent.com/LennysNewsletter/lennys-newsletterpodcastdata/main/podcasts/elena-verna-40.md"
]

def download_samples():
    # Make sure we're saving to data/transcripts relative to project root
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "transcripts"))
    os.makedirs(target_dir, exist_ok=True)
    
    for url in TRANSCRIPTS:
        filename = url.split("/")[-1]
        print(f"Downloading {filename}...")
        try:
            urllib.request.urlretrieve(url, os.path.join(target_dir, filename))
        except Exception as e:
            print(f"Failed to download {filename}: {e}")

if __name__ == "__main__":
    download_samples()
