from duckduckgo_search import DDGS
import urllib.parse

class SearchTool:
    """
    Fetches real-time images with a robust Google Images fallback.
    """
    
    def search_part_image(self, part_name: str, bike_model: str) -> str:
        """
        Searches for a specific technical image or diagram.
        """
        print(f"🔍 SEARCH CALL: Looking for images of '{part_name}' for '{bike_model}'...")
        
        # Clean up the query
        query = f"{bike_model} {part_name} location diagram real photo"
        
        # Create a fallback Google Images URL
        encoded_query = urllib.parse.quote(query)
        google_fallback_url = f"https://www.google.com/search?tbm=isch&q={encoded_query}"

        try:
            # Attempt Live Fetch (DuckDuckGo)
            with DDGS() as ddgs:
                results = list(ddgs.images(
                    query, 
                    region="in-en", 
                    safesearch="moderate", 
                    max_results=1
                ))
                
                if results:
                    img_url = results[0]['image']
                    title = results[0]['title']
                    
                    return (
                        f"### 📸 Visual Guide: {part_name.title()}\n"
                        f"Here is the visual reference for the **{part_name}**:\n\n"
                        f"![{title}]({img_url})\n\n"
                        f"🔗 [See more images on Google]({google_fallback_url})"
                    )
                    
        except Exception as e:
            print(f"⚠️ Search API failed: {e}")
        
        # FAIL-SAFE RESPONSE (If DDG fails, we still give a useful link)
        return (
            f"### 📸 Visual Reference\n"
            f"I couldn't embed the image directly right now, but I found the search results for you.\n\n"
            f"👉 **[Click here to view {part_name} photos on Google]({google_fallback_url})**"
        )

if __name__ == "__main__":
    tool = SearchTool()
    print(tool.search_part_image("spark plug", "Honda Activa 5G"))