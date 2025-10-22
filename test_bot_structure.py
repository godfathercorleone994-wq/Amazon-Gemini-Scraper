#!/usr/bin/env python3
"""
Simple test to verify bot can be imported and basic structure is valid
This doesn't require actual credentials to run
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        from config.settings import settings
        print("✅ config.settings imported")
    except Exception as e:
        print(f"❌ Failed to import config.settings: {e}")
        return False
    
    try:
        from utils.logger import logger
        print("✅ utils.logger imported")
    except Exception as e:
        print(f"❌ Failed to import utils.logger: {e}")
        return False
    
    try:
        from storage.mongodb_client import mongodb_client
        print("✅ storage.mongodb_client imported")
    except Exception as e:
        print(f"❌ Failed to import storage.mongodb_client: {e}")
        return False
    
    try:
        from storage.redis_cache import redis_cache
        print("✅ storage.redis_cache imported")
    except Exception as e:
        print(f"❌ Failed to import storage.redis_cache: {e}")
        return False
    
    try:
        from core.scraper_agent import ScraperAgent
        print("✅ core.scraper_agent imported")
    except Exception as e:
        print(f"❌ Failed to import core.scraper_agent: {e}")
        return False
    
    try:
        from core.gemini_extractor import GeminiExtractor
        print("✅ core.gemini_extractor imported")
    except Exception as e:
        print(f"❌ Failed to import core.gemini_extractor: {e}")
        return False
    
    return True

def test_bot_structure():
    """Test bot_main.py structure without actually running it"""
    print("\nTesting bot structure...")
    
    try:
        # Just check if file can be compiled
        import py_compile
        py_compile.compile('bot_main.py', doraise=True)
        print("✅ bot_main.py syntax is valid")
    except Exception as e:
        print(f"❌ bot_main.py has syntax errors: {e}")
        return False
    
    return True

def test_env_example():
    """Test that .env.example exists and has required variables"""
    print("\nTesting .env.example...")
    
    if not os.path.exists('.env.example'):
        print("❌ .env.example not found")
        return False
    
    with open('.env.example', 'r') as f:
        content = f.read()
    
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'MONGODB_ATLAS_URI',
        'REDIS_URL',
        'GEMINI_API_KEY'
    ]
    
    all_found = True
    for var in required_vars:
        if var in content:
            print(f"✅ {var} found in .env.example")
        else:
            print(f"❌ {var} not found in .env.example")
            all_found = False
    
    return all_found

def test_documentation():
    """Test that documentation files exist"""
    print("\nTesting documentation...")
    
    docs = [
        'README.md',
        'TELEGRAM_BOT_PT.md',
        'COMANDOS.md',
        'start_bot.sh'
    ]
    
    all_exist = True
    for doc in docs:
        if os.path.exists(doc):
            print(f"✅ {doc} exists")
        else:
            print(f"❌ {doc} not found")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests"""
    print("=" * 60)
    print("Amazon Scraper Telegram Bot - Structure Tests")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Bot Structure", test_bot_structure()))
    results.append(("Environment Config", test_env_example()))
    results.append(("Documentation", test_documentation()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All tests passed! Bot structure is valid.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env")
        print("2. Configure your credentials")
        print("3. Run: ./start_bot.sh")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
