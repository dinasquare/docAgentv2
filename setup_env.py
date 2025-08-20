"""
Simple script to set up the .env file with working configuration.
"""

import os
from pathlib import Path

def create_env_file():
    """Create .env file from env.example."""
    
    # Read the example file
    example_path = Path("env.example")
    env_path = Path(".env")
    
    if not example_path.exists():
        print("❌ env.example not found")
        return False
    
    # Read example content
    with open(example_path, 'r') as f:
        content = f.read()
    
    # Update OCR engine to easyocr for better compatibility
    content = content.replace("OCR_ENGINE=paddleocr", "OCR_ENGINE=easyocr")
    
    # Write to .env
    with open(env_path, 'w') as f:
        f.write(content)
    
    print("✅ .env file created successfully")
    print("🔑 Make sure to update GEMINI_API_KEY with your actual API key")
    
    return True

def main():
    """Main function."""
    print("⚙️ Setting up environment file...")
    
    if create_env_file():
        print("\n✅ Setup complete!")
        print("Next: Run 'python verify_setup.py' to test your configuration")
    else:
        print("\n❌ Setup failed!")

if __name__ == "__main__":
    main()
