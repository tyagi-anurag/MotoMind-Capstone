import urllib.parse

class SearchTool:
    """
    Generates direct Google Image Search links for bike parts.
    Reliable, fast, and crash-proof.
    """
    
    def search_part_image(self, part_name: str, bike_model: str) -> str:
        """
        Returns a clickable link to view images of the part.
        """
        print(f"🔍 SEARCH CALL: generating link for '{part_name}' on '{bike_model}'...")
        
        query = f"{bike_model} {part_name} location diagram real photo"
        encoded_query = urllib.parse.quote(query)
        google_url = f"https://www.google.com/search?tbm=isch&q={encoded_query}"
        
        # Return Markdown Link directly
        return (
            f"### 📸 Visual Reference: {part_name.title()}\n\n"
            f"Tap the link below to see photos and diagrams:\n"
            f"👉 **[View {part_name} on Google Images]({google_url})**"
        )

if __name__ == "__main__":
    tool = SearchTool()
    print(tool.search_part_image("battery", "Hero Splendor"))