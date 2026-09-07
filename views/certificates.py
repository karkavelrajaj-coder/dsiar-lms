from bson import ObjectId

import streamlit as st

from utils.auth import require_role
from utils.certificate_image import build_certificate
from utils.db import certificates_col, courses_col

user = require_role("student", "instructor", "admin")

st.title("🏆 My certificates")

certs = list(certificates_col().find({"user_id": user["id"]}))

if not certs:
    st.info(
        "No certificates yet. A certificate is issued automatically once you've "
        "completed every lesson in a course AND your assignment has been approved."
    )
    st.stop()

for cert in certs:
    course = courses_col().find_one({"_id": ObjectId(cert["course_id"])})
    course_title = course["title"] if course else "Unknown course"

    with st.container(border=True):
        st.subheader(f"🎓 {course_title}")
        st.caption(f"Certificate ID: {cert['cert_id']} · Issued {cert['issued_at'].strftime('%B %d, %Y')}")

        image_bytes = build_certificate(
            student_name=user["name"],
            course_title=course_title,
            cert_id=cert["cert_id"],
            issued_at=cert["issued_at"],
        )
        st.image(image_bytes, use_container_width=True)
        st.download_button(
            "Download certificate (PNG)",
            data=image_bytes,
            file_name=f"dsiar-certificate-{course_title.replace(' ', '_')}.png",
            mime="image/png",
            key=f"dl_{cert['cert_id']}",
        )
