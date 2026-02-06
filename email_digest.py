import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import requests
import os

# Email credentials from environment variables (set in GitHub Secrets)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'your_email@gmail.com')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', 'your_app_password')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL', 'mark@maplanning.co.uk')

def score_lead(application):
    """Score each lead based on Mark's business criteria"""
    score = 0
    reasons = []
    
    applicant = str(application.get('applicant', '')).lower()
    description = str(application.get('description', '')).lower()
    status = str(application.get('status', '')).lower()
    
    # Positive scoring
    company_keywords = ['ltd', 'limited', 'architects', 'developments', 'properties']
    if any(keyword in applicant for keyword in company_keywords):
        score += 3
        reasons.append("✓ Company applicant")
    
    commercial_keywords = ['retail', 'commercial', 'mixed use', 'office', 'shop']
    if any(keyword in description for keyword in commercial_keywords):
        score += 3
        reasons.append("✓ Commercial project")
    
    if 'refused' in status or 'reject' in status:
        score += 2
        reasons.append("✓ Refused (appeal opportunity)")
    
    # Negative scoring
    if 'hmo' in description:
        score -= 5
        reasons.append("✗ HMO")
    
    extension_keywords = ['extension', 'basement', 'loft']
    if any(keyword in description for keyword in extension_keywords):
        score -= 5
        reasons.append("✗ Extension/Basement")
    
    if score >= 5:
        priority = "A - HIGH PRIORITY"
    elif score >= 2:
        priority = "B - MEDIUM"
    else:
        priority = "C - LOW"
    
    return score, priority, reasons

def fetch_weekly_leads():
    """Fetch last 7 days of planning applications"""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    url = "https://planningdata.london.gov.uk/api-guest/applications"
    params = {
        "date_received_start": start_date.strftime("%Y-%m-%d"),
        "date_received_end": end_date.strftime("%Y-%m-%d"),
        "page_size": 100
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        applications = []
        for app in data.get('data', []):
            applications.append({
                'reference': app.get('planning_application_reference', 'N/A'),
                'address': app.get('site_address', 'N/A'),
                'description': app.get('development_description', 'N/A'),
                'applicant': app.get('applicant_name', 'N/A'),
                'status': app.get('status_description', 'N/A'),
                'date': app.get('date_received', 'N/A'),
                'link': f"https://planningdata.london.gov.uk/planning-application/{app.get('planning_application_reference', '')}"
            })
        
        return applications
    
    except Exception as e:
        print(f"❌ Error fetching data: {str(e)}")
        return []

def generate_email_html(top_leads):
    """Generate HTML email with top leads"""
    
    if not top_leads:
        return "<p>No qualified leads found this week.</p>"
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .lead {{ 
                border: 1px solid #ddd; 
                padding: 15px; 
                margin: 15px 0; 
                border-radius: 5px;
            }}
            .priority-a {{ border-left: 5px solid #28a745; }}
            .priority-b {{ border-left: 5px solid #ffc107; }}
            .score {{ 
                background: #007bff; 
                color: white; 
                padding: 5px 10px; 
                border-radius: 3px;
                display: inline-block;
            }}
            .button {{
                background: #007bff;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                display: inline-block;
                margin: 5px 5px 5px 0;
            }}
            .reasons {{ color: #666; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <h2>🏗️ Weekly Lead Digest - Top Opportunities</h2>
        <p><strong>Week ending:</strong> {datetime.now().strftime("%B %d, %Y")}</p>
        <p>Here are your top {len(top_leads)} qualified leads from London Planning Datahub:</p>
        <hr>
    """
    
    for idx, lead in enumerate(top_leads, 1):
        priority_class = "priority-a" if "A -" in lead['priority'] else "priority-b"
        search_query = f"{lead['applicant']} UK contact architect developer".replace(' ', '+')
        google_search_url = f"https://www.google.com/search?q={search_query}"
        
        html += f"""
        <div class="lead {priority_class}">
            <h3>{idx}. {lead['priority']} <span class="score">Score: {lead['score']}</span></h3>
            <p><strong>Address:</strong> {lead['address']}</p>
            <p><strong>Applicant:</strong> {lead['applicant']}</p>
            <p><strong>Description:</strong> {lead['description'][:200]}...</p>
            <p><strong>Status:</strong> {lead['status']}</p>
            <p class="reasons"><strong>Why this scored high:</strong> {lead['reasons']}</p>
            <a href="{lead['link']}" class="button">View Application</a>
            <a href="{google_search_url}" class="button">Research Contact</a>
        </div>
        """
    
    html += """
        <hr>
        <p style="color: #666; font-size: 0.9em;">
            Automated digest from your Lead Sourcing Engine.
        </p>
    </body>
    </html>
    """
    
    return html

def send_email(subject, html_content):
    """Send email via Gmail SMTP"""
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("✅ Email sent successfully!")
        return True
    
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False

def main():
    """Main function to run weekly digest"""
    
    print("🔍 Fetching weekly leads...")
    applications = fetch_weekly_leads()
    
    if not applications:
        print("⚠️ No applications found.")
        return
    
    print(f"📊 Found {len(applications)} applications. Scoring...")
    
    scored_leads = []
    for app in applications:
        score, priority, reasons = score_lead(app)
        
        if score >= 2:
            scored_leads.append({
                **app,
                'score': score,
                'priority': priority,
                'reasons': ' | '.join(reasons)
            })
    
    scored_leads.sort(key=lambda x: x['score'], reverse=True)
    top_5 = scored_leads[:5]
    
    if not top_5:
        print("⚠️ No qualified leads found this week.")
        return
    
    print(f"✅ Found {len(top_5)} qualified leads. Sending email...")
    
    subject = f"🏗️ Weekly Lead Digest - {len(top_5)} Qualified Opportunities"
    html_content = generate_email_html(top_5)
    
    send_email(subject, html_content)

if __name__ == "__main__":
    main()
```

4. Click **"Commit new file"**

**✅ Done when:** You have 4 files in your repository

---

### **STEP 4: DEPLOY TO STREAMLIT CLOUD (10 minutes)**

1. Go to: https://streamlit.io/cloud
2. Click **"Sign up"** (use your GitHub account to sign in)
3. Click **"New app"**
4. Select:
   - Repository: `mark-lead-sourcing`
   - Branch: `main`
   - Main file path: `app.py`
5. Click **"Deploy!"**

**Wait 2-3 minutes.** You'll see a URL like: `https://mark-lead-sourcing-xxxxx.streamlit.app`

**✅ Done when:** The app loads and you see "Lead Sourcing Engine for MA Planning"

---

### **STEP 5: SET UP EMAIL SECRETS IN GITHUB (5 minutes)**

Now we need to add your email credentials so the automated script can send emails.

1. **Get Gmail App Password first:**
   - Go to: https://myaccount.google.com/security
   - Enable "2-Step Verification"
   - Search "App passwords"
   - Create one for "Mail"
   - **Copy the 16-character password**

2. **Go back to your GitHub repository**

3. Click **"Settings"** (top right)

4. In the left sidebar, click **"Secrets and variables"** → **"Actions"**

5. Click **"New repository secret"**

6. Add three secrets (one at a time):

   **Secret 1:**
   - Name: `SENDER_EMAIL`
   - Value: `inger.balaj@gmail.com` (your actual Gmail)
   - Click "Add secret"

   **Secret 2:**
   - Name: `SENDER_PASSWORD`
   - Value: (paste the 16-character app password)
   - Click "Add secret"

   **Secret 3:**
   - Name: `RECIPIENT_EMAIL`
   - Value: `mark@maplanning.co.uk`
   - Click "Add secret"

**✅ Done when:** You see 3 secrets listed

---

### **STEP 6: TEST THE EMAIL DIGEST (2 minutes)**

1. In your GitHub repository, click **"Actions"** (top menu)
2. Click **"Weekly Lead Digest"** (left sidebar)
3. Click **"Run workflow"** dropdown (right side)
4. Click green **"Run workflow"** button

**Wait 1-2 minutes**, then check Mark's email. He should receive the digest!

**✅ Done when:** Email arrives in Mark's inbox

---

### **STEP 7: SHARE WITH MARK (1 minute)**

Send Mark this information:
```
Hi Mark,

Your Lead Sourcing Engine is live!

🌐 WEB APP: [paste your Streamlit URL here]
- Use this to search for leads anytime
- Filter by date, council, priority score
- Export to CSV

📧 WEEKLY EMAILS:
- Every Monday at 9 AM
- Top 5 qualified leads automatically sent to your email
- Includes scoring breakdown and action buttons

Let me know what you think!
