# backend/test_tools.py
print("=== TESTING TOOL IMPORT ===")

try:
    from tools.system_tools import ALL_TOOLS
    print(f"✅ SUCCESS: Loaded {len(ALL_TOOLS)} tools")
    print("Tool names:")
    for tool in ALL_TOOLS:
        print(f"   • {tool.name}")
except Exception as e:
    print("❌ FAILED to import tools:", e)

print("\nDone.")