import os
from dotenv import load_dotenv
load_dotenv()
print('GOOGLE_API_KEY present:', bool(os.getenv('GOOGLE_API_KEY')))
try:
    import google.generativeai as genai
    print('google.generativeai version:', getattr(genai, '__version__', 'unknown'))
    print('google.generativeai module:', genai.__file__)
except Exception as e:
    print('google.generativeai import failed:', e)
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    print('langchain_google_genai available')
    import langchain_google_genai
    print('langchain_google_genai version:', getattr(langchain_google_genai, '__version__', 'unknown'))
except Exception as e:
    print('langchain_google_genai import failed:', e)
try:
    import google.auth
    print('google.auth available:', google.auth.__file__)
except Exception as e:
    print('google.auth import failed:', e)
