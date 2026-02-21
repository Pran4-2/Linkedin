# LinkedIn Easy Apply Automation Agent

An intelligent Python bot that **searches, prioritises, and automatically applies** to LinkedIn Easy Apply jobs. It fills all form fields, answers screening questions (using the STAR method where relevant), attaches your CV and Cover Letter, logs every application to a CSV file, and generates weekly summaries.

---

## Features

| Capability | Details |
|---|---|
| 🔍 Smart Job Search | Searches by role, location, keyword, experience level, and date posted |
| 📝 Easy Apply Automation | Fills text inputs, dropdowns, radios, checkboxes, and file-upload fields |
| 🧠 Intelligent Q&A | Answers screening questions; uses STAR-method responses for behavioural questions |
| 📎 Document Attachment | Automatically attaches your CV and Cover Letter |
| 📊 CSV Logging | Every application logged to `Applications.csv` with title, company, date, status, and notes |
| 📈 Weekly Summary | Console report of total applied, response rate, and follow-ups due |
| ⚙️ Fully Configurable | Single `config.yaml` controls all behaviour – no code changes needed |

---

## Project Structure

```
Linkedin/
├── main.py                  # Entry point – run this
├── linkedin_bot.py          # Selenium automation core
├── form_filler.py           # Easy Apply multi-step form handler
├── question_answerer.py     # Screening question logic (STAR method)
├── logger.py                # CSV logging + weekly summary
├── summary.py               # Standalone summary CLI
├── config.yaml              # ← Edit this with YOUR details
├── requirements.txt         # Python dependencies
├── documents/               # Place your CV.pdf and CoverLetter.pdf here
│   └── .gitkeep
├── tests/
│   ├── test_logger.py
│   └── test_question_answerer.py
└── Applications.csv         # Auto-created when the bot first runs
```

---

## Step-by-Step Setup & Run Instructions

### Step 1 – Prerequisites

- Python **3.10 or newer** installed ([python.org](https://www.python.org/downloads/))
- Google Chrome installed (the bot uses ChromeDriver managed automatically)
- A LinkedIn account

### Step 2 – Clone / Download the repository

```bash
git clone https://github.com/Pran4-2/Linkedin.git
cd Linkedin
```

### Step 3 – Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 4 – Add your CV and Cover Letter

Place your CV and Cover Letter **PDF files** in the `documents/` folder:

```
documents/
├── CV.pdf
└── CoverLetter.pdf
```

> The file names must match the paths in `config.yaml` (see Step 5).

### Step 5 – Edit `config.yaml`

Open `config.yaml` in any text editor and fill in **your** details.  
Key sections to update:

```yaml
linkedin:
  email: "your_real_email@gmail.com"   # ← your LinkedIn login
  password: "your_password"            # ← your LinkedIn password

personal:
  first_name: "Your First Name"
  last_name:  "Your Last Name"
  email:      "your_real_email@gmail.com"
  phone:      "+91 XXXXXXXXXX"

documents:
  cv_path:           "documents/CV.pdf"
  cover_letter_path: "documents/CoverLetter.pdf"
```

The default job targets and location are already set for this use case:

```yaml
search:
  job_titles:
    - "SOC Analyst"
    - "Incident Response"
    - "Security Operations Center Analyst"
  locations:
    - "Bangalore"
  easy_apply_only: true
  max_applications: 50
```

Adjust `max_applications` to control how many jobs the bot applies to per session.

### Step 6 – Run the bot

```bash
python main.py
```

A Chrome browser window will open, log in to LinkedIn, search for the configured roles in Bangalore, and start applying automatically.

#### Optional flags

| Flag | Effect |
|---|---|
| `--config path/to/config.yaml` | Use a different config file |
| `--dry-run` | Open browser and search, but **do not submit** any applications |
| `--summary` | Print the weekly summary and exit (no browser) |

```bash
# Print summary only
python main.py --summary

# Or use the standalone summary script
python summary.py --csv Applications.csv

# Dry run (safe to test without submitting)
python main.py --dry-run
```

### Step 7 – Review your applications

All applications are saved to **`Applications.csv`** automatically:

| Job Title | Company | Date Applied | Method | Status | Follow-up | Notes |
|---|---|---|---|---|---|---|
| SOC Analyst | Acme Corp | 2024-06-01 14:23 | LinkedIn Easy Apply | Applied | | |

### Step 8 – Run the tests (optional, for developers)

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Configuration Reference

| Section | Key | Description |
|---|---|---|
| `linkedin` | `email`, `password` | LinkedIn login credentials |
| `search` | `job_titles` | List of job titles to search |
| `search` | `locations` | List of locations (e.g. `Bangalore`) |
| `search` | `easy_apply_only` | Only show Easy Apply jobs |
| `search` | `max_applications` | Safety cap per session |
| `search` | `date_posted` | `past_24_hours`, `past_week`, `past_month`, `any_time` |
| `personal` | — | Name, phone, city, country, LinkedIn URL |
| `documents` | `cv_path` | Path to your CV PDF |
| `documents` | `cover_letter_path` | Path to your Cover Letter PDF |
| `eligibility` | `legally_authorized` | Work authorisation answer |
| `eligibility` | `require_sponsorship` | Visa sponsorship answer |
| `background` | `years_of_experience` | Used for numeric form fields |
| `answers.yes_no` | — | Custom yes/no answers for specific questions |
| `answers.star_answers` | — | Custom STAR-method answers for behavioural questions |
| `browser` | `headless` | Run Chrome without a visible window |
| `logging` | `csv_path` | Output CSV file path |

---

## Security Note

> **Never commit your real credentials to Git.**  
> Keep `config.yaml` with real passwords out of version control by adding it to `.gitignore`, or use environment variables.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Config file not found` | Make sure `config.yaml` exists in the same folder as `main.py` |
| `LinkedIn credentials are not set` | Edit `config.yaml` – replace the placeholder email/password |
| Bot gets stuck on CAPTCHA | Run with `headless: false`, solve the CAPTCHA manually once, then restart |
| File upload fails | Ensure `documents/CV.pdf` exists and the path in `config.yaml` is correct |
| ChromeDriver error | Run `pip install --upgrade webdriver-manager` |
