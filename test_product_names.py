#!/usr/bin/env python3
"""Test script to verify Fuxion product names are preserved correctly"""

from src.chat import ChatPipeline

def test_product_name_preservation():
    try:
        print("🔍 Testing Fuxion product name preservation...")
        chat = ChatPipeline()
        
        # Test specific product queries to see if names are preserved
        test_queries = [
            "Tell me about ALPHA BALANCE",
            "What is BEAUTY-IN?",
            "Give me information about BERRY BALANCE",
            "Tell me about BIOPRO+ SPORT",
            "What products do you have for weight loss?"
        ]
        
        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"🔍 Testing query: '{query}'")
            print(f"{'='*60}")
            
            # Get response using the chat pipeline
            response = chat.ask(query, "test_user")
            answer = response.get('answer', '')
            
            print(f"🤖 Response length: {len(answer)} characters")
            print(f"📄 Response preview: {answer[:200]}...")
            
            # Check for specific product names in the response
            product_names = [
                'ALPHA BALANCE', 'BEAUTY-IN', 'BERRY BALANCE', 'BIOPRO+ SPORT',
                'CAFÉ & CAFÉ FIT', 'CHOCOLATE FIT', 'FLORA LIV', 'PASSION',
                'PRUNEX1', 'THERMO T3', 'VITA XTRA T+', 'CAFÉ GANOMAX'
            ]
            
            found_products = []
            for product_name in product_names:
                if product_name in answer:
                    found_products.append(product_name)
            
            if found_products:
                print(f"✅ Found product names: {', '.join(found_products)}")
            else:
                print("⚠️ No specific product names found in response")
            
            # Check for SKU numbers
            import re
            sku_pattern = r'SKU:\s*(\d+)'
            skus = re.findall(sku_pattern, answer)
            if skus:
                print(f"✅ Found SKUs: {', '.join(skus)}")
            else:
                print("⚠️ No SKU numbers found in response")
        
        print(f"\n{'='*60}")
        print("🎯 Testing complete! Check above for product name preservation.")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_product_name_preservation()
