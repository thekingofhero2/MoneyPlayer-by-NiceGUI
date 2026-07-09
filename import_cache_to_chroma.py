"""Import cache_videos to ChromaDB with folder names as labels"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app_videomaker.services.material_library import add_video_material, _get_chroma_client, _collection_name

def import_cache_videos():
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "storage", "cache_videos")
    
    if not os.path.exists(cache_dir):
        print(f"Cache directory not found: {cache_dir}")
        return
    
    # Ensure collection exists
    client = _get_chroma_client()
    try:
        client.get_collection(name=_collection_name)
    except Exception:
        client.create_collection(name=_collection_name, metadata={"description": "Local video material library"})
    
    total_added = 0
    folders_processed = []
    
    for folder_name in os.listdir(cache_dir):
        folder_path = os.path.join(cache_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue
        
        # Use folder name as search_term (label)
        search_term = folder_name.strip()
        count = 0
        
        for filename in os.listdir(folder_path):
            if filename.endswith('.mp4'):
                video_path = os.path.join(folder_path, filename)
                if add_video_material(
                    video_path=video_path,
                    search_term=search_term,
                    provider="cache_videos",
                    duration=0
                ):
                    count += 1
        
        if count > 0:
            folders_processed.append((search_term, count))
            total_added += count
            print(f"Added {count} videos for label: {search_term}")
    
    print(f"\n=== Summary ===")
    print(f"Total folders: {len(folders_processed)}")
    print(f"Total videos added: {total_added}")
    
    # Verify
    collection = client.get_collection(name=_collection_name)
    print(f"ChromaDB collection count: {collection.count()}")

if __name__ == "__main__":
    import_cache_videos()
