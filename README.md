# D'siar Tech LMS

A simple, smart, strong Learning Management System built with Streamlit +
MongoDB Atlas, streaming lesson videos from YouTube. Built for D'siar Tech's
course catalog (Python, AI, ML, Deep Learning, Gen AI, Data Science,
Cybersecurity, Quantum Computing, R, BI, Fintech, Blockchain, C Programming).

## Roles (RBAC)

| Role | Can do |
|---|---|
| **Admin** | Everything: create/manage all courses & content, manage users and roles, grade any submission, assign courses to instructors |
| **Instructor** ("staff / user") | Manage content and grade submissions only for courses assigned to them by an admin. Can also browse/enroll as a learner. |
| **Student** | Browse catalog, enroll, watch lessons, download slides/notebooks/datasets, submit assignments, track progress |

Public sign-up only ever creates a **student** account. Instructor and admin
accounts are created from the **Manage Users** page by an existing admin.
The very first admin account is auto-created on first run from the
`SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` secrets — log in with those, then
change the password by creating a new admin and deleting the seed one (or
add a "change password" feature later).

## Project structure

```
dsiar-lms/
├── app.py                     # Entry point — login gate + role-based navigation
├── requirements.txt
├── .streamlit/
│   └── secrets.toml.example   # Copy to secrets.toml locally; never commit the real one
├── utils/
│   ├── db.py                  # MongoDB connection + collection helpers
│   └── auth.py                # Password hashing, sessions, RBAC guards
└── views/
    ├── login.py                # Log in / student sign-up
    ├── catalog.py               # Student: browse + enroll
    ├── my_learning.py           # Student: enrolled courses + progress
    ├── course_player.py         # Student: video + slides/colab/dataset tabs
    ├── assignments.py           # Student: submit assignments
    ├── admin_courses.py         # Admin/Instructor: manage courses, modules, lessons
    ├── admin_submissions.py     # Admin/Instructor: post assignments, grade
    └── admin_users.py           # Admin only: create staff accounts, change roles
```

## MongoDB Atlas setup (free tier)

1. Create a free **M0** cluster at cloud.mongodb.com.
2. Database Access → add a user with a strong password.
3. Network Access → allow access from anywhere (`0.0.0.0/0`) for Streamlit Cloud.
4. Copy your connection string (Drivers → Python).

Keep PPTs, datasets, and assignment docs **out of MongoDB** — the free tier
is only 512MB. Store them in your GitHub repo, Google Drive, or GitHub
Releases, and paste the link when creating a lesson.

## Local setup

```bash
git clone <your-repo-url>
cd dsiar-lms
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml with your Mongo URI and seed admin credentials
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to share.streamlit.io → **New app** → pick this repo/branch → main file `app.py`.
3. In **App settings → Secrets**, paste the same keys as `secrets.toml.example`
   with your real values.
4. Deploy. Every push to `main` auto-redeploys.

## Roadmap

- **Phase 1 (this build):** auth + RBAC, course catalog, video player,
  resource links, progress tracking, admin/instructor content management,
  assignment submission & grading.
- **Phase 2:** auto-generated PDF certificates, admin analytics dashboard,
  bulk course import.
- **Phase 3:** quizzes (potential integration with D'siar's own QuizWhiz Hub),
  discussion/Q&A per lesson, email notifications, paid-course checkout.
