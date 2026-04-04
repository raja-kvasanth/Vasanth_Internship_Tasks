import os
from dotenv import load_dotenv

from langchain_community.document_loaders import YoutubeLoader

from langchain.chat_models import init_chat_model

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import chain, RunnableBranch, RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

import zipfile

load_dotenv()

os.environ['GOOGLE_API_KEY'] = os.getenv('gemini_key')

# Model
llm = init_chat_model(
    'google-genai:gemini-2.5-flash'
)

system_message = 'You are an Professional Article Writer specializing in writing articles for Medium, LinkedIn, and tech blogs.'

human_message = '''
Transform YouTube transcript into **engaging, professional articles** with:

**CRITICAL INSTRUCTIONS**:
- **IGNORE** Introductionary notes like welcome, In this video
- **IGNORE** all channel names, "subscribe", "like", "comment", "follow", "check description" 
- **IGNORE** marketing phrases: "my course", "my discord", "affiliate links", "sponsors"
- **FOCUS ONLY** on technical content, code, tutorials, actionable insights

**MANDATORY ARTICLE STRUCTURE** (exact Medium/LinkedIn format):
- Write in **first-person professional tone** 
- Use **bold subheadings**, **numbered lists**.
- Include **code snippets** for technical videos
- Make **Actionable Steps** copy-paste ready
- End with **short summary of the article**
{transcript}
'''
summarizer_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(system_message),
    HumanMessagePromptTemplate.from_template(human_message)
])


def extract_transcript(link: str) -> str:
  """
  Extract YouTube transcript using YoutubeLoader
  Input: YouTube URL → Output: Transcript text
  """
  loader = YoutubeLoader.from_youtube_url(link)
  docs = loader.load()
  return docs[0].page_content


base_summarizer = (
    RunnablePassthrough() 
    | RunnableLambda(extract_transcript)
    | summarizer_prompt 
    | llm 
    | StrOutputParser()
)

system_prompt = """
You are a recursive summarization engine.

Your job:
- Continuously summarize incoming content
- Maintain a concise but complete running summary
- When content grows large, compress older information
- Preserve key technical details, concepts, and relationships
- Output ONLY the updated summary

Think of this as:
A rolling summary that improves as more text arrives and prepares a production ready article.
"""

def get_text_chunks(text, chunk_size=5000, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""],  
    )
    return splitter.split_text(text)


agent = create_agent(
    model=llm,
    tools=[],  
    system_prompt = system_message,
    middleware=[
        SummarizationMiddleware(
            model=llm,
            trigger=("tokens", 1000),   
            keep=("tokens", 200),       
        ),
    ],
)
agent

def recursive_summarize(text, agent=agent):
    chunks = get_text_chunks(text)
    running_summary = ""

    for chunk in chunks:
        response = agent.invoke({
            "messages": [
                {
                    "role": "user",
                    "content": f"""
You are summarizing technical content.

Current summary:
{running_summary}

New content:
{chunk}

While summarizing teh text in the form of article strictly follow
**CRITICAL INSTRUCTIONS**:
- **IGNORE** Introductionary notes like welcome, In this video
- **IGNORE** all channel names, "subscribe", "like", "comment", "follow", "check description"
- **IGNORE** marketing phrases: "my course", "my discord", "affiliate links", "sponsors"
- **FOCUS ONLY** on technical content, code, tutorials, actionable insights

**MANDATORY ARTICLE STRUCTURE** (exact Medium/LinkedIn format):
- Write in **first-person professional tone**
- Use **bold subheadings**, **numbered lists**.
- Include **code snippets** for technical videos
- Make **Actionable Steps** copy-paste ready
- End with **short summary of the article**
"""
                }
            ]
        })

        running_summary = response["messages"][-1].content

    return running_summary

long_summarizer = RunnablePassthrough() | RunnableLambda(extract_transcript) | RunnableLambda(recursive_summarize)
long_summarizer


def estimate_transcript_length(link: str) -> bool:
    """Quick length estimator (characters → tokens)."""
    transcript = extract_transcript(link)
    return len(transcript) >= 1000 


system_message = """You are a Senior Frontend Web Developer with 10+ years experience in HTML5, CSS3, and modern JavaScript (ES6+).

Your task: Generate COMPLETE, PRODUCTION-READY frontend code based on user requirements.

**MANDATORY OUTPUT FORMAT** (exact delimiters):
--html--
[html code here]
--html--

--css--
[css code here]
--css--

--js--
[java script code here]
--js--
"""

human_message = '''
Create a **production-ready article webpages** in the style of **Medium, Dev.to, Hashnode, and Substack**.

**MANDATORY REQUIREMENTS**:
- **Mobile-first responsive design** (perfect on all devices)
- **Clean, modern typography** (system fonts + readability first)
- **Medium-like article layout** with card-based design
- **Dark/light theme toggle**
- **Smooth animations** and **scroll effects**
- **SEO optimized** with proper meta tags
- **Accessibility compliant** (ARIA labels, keyboard navigation)

**CONTENT TO USE**: {article_content}
'''

web_dev_template = ChatPromptTemplate.from_messages([system_message, human_message])
webpage_chain = web_dev_template | llm | StrOutputParser()

smart_summarizer = RunnableBranch(
    
    (RunnableLambda(estimate_transcript_length), long_summarizer),
    
    
    base_summarizer) | web_dev_template | llm | StrOutputParser()

article = smart_summarizer.invoke("https://youtu.be/MZpGazgm4OQ?si=MS6NXG9x3V_xIQrI")

with open('index.html', 'w') as file:
        file.write(article.split('--html--')[1])

with open('style.css', 'w') as file:
    file.write(article.split('--css--')[1])

with open('script.js', 'w') as file:
    file.write(article.split('--js--')[1])

with zipfile.ZipFile('website.zip', 'w') as zip:
    zip.write('index.html')
    zip.write('style.css')
    zip.write('script.js')
