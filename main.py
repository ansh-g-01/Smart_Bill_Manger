import streamlit as st
import requests
from PIL import Image
from config import EMAIL, APP_PASSWORD, OCR_API_KEY
from db_manager import DatabaseManager
from email_sender import EmailSender
from extractor import extract_summary_from_ocr, extract_user_payments

# === Streamlit App ===
st.set_page_config(
    page_title="Shared Expenses",
    page_icon="favicon.png",
    layout="centered"
)

db = DatabaseManager()
email_sender = EmailSender(EMAIL, APP_PASSWORD, db)

st.title("🧾 Shared Expenses Tracker")

# === OCR Function using OCR.Space API ===
def extract_text_from_image_ocrspace(image_file, api_key):
    url = "https://api.ocr.space/parse/image"
    image_bytes = image_file.read()

    response = requests.post(
        url,
        files={"file": ("bill.jpg", image_bytes)},
        data={
            "apikey": api_key,
            "language": "eng",
            "isOverlayRequired": False
        }
    )

    try:
        result = response.json()
        if result.get("IsErroredOnProcessing"):
            raise Exception(result.get("ErrorMessage", ["OCR error occurred"])[0])
        
        parsed_results = result.get("ParsedResults")
        if parsed_results and parsed_results[0].get("ParsedText"):
            return parsed_results[0]["ParsedText"]
        else:
            raise Exception("No text found in image.")
    
    except Exception as e:
        return f"OCR failed: {str(e)}"

# === Upload Main Bill to Add Users ===
uploaded_file = st.file_uploader("📄 Upload a bill image (for adding users)", type=["png", "jpg", "jpeg"])

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Bill", use_column_width=True)

    ocr_text = extract_text_from_image_ocrspace(uploaded_file, OCR_API_KEY)

    st.subheader("🔍 OCR Text")
    st.text_area("Extracted Text", ocr_text, height=200)

    with st.spinner("🧠 Extracting user summary from OCR..."):
        try:
            extracted_data = extract_summary_from_ocr(ocr_text)
            st.subheader("📋 Extracted Data")
            st.json(extracted_data)

            if st.button("✅ Save to DB"):
                db.add_or_update_user(extracted_data)
                st.success("Saved successfully!")
        except Exception as e:
            st.error(f"Extraction failed: {e}")

# === Send Emails ===
if st.button("📬 Send Balance Emails"):
    email_sender.send_all()
    st.success("✅ All balance emails sent!")

# === View All Users ===
if st.button("📊 View All Users"):
    users = db.get_all_users()
    st.write("### 👥 All Users & Balances")
    st.table(users)

# === Upload Paid Bill for Deduction ===
with st.expander("📤 Upload Paid Bills (for Deduction)"):
    paid_file = st.file_uploader(
        "Upload a bill image showing individual paid amounts",
        type=["png", "jpg", "jpeg"],
        key="deduct_upload"
    )

    if paid_file:
        st.image(paid_file, caption="Uploaded Paid Bill", use_column_width=True)

        ocr_text = extract_text_from_image_ocrspace(paid_file, OCR_API_KEY)

        with st.spinner("🧠 Extracting individual user payments..."):
            user_entries = extract_user_payments(ocr_text)

        if user_entries:
            st.subheader("📋 Extracted Payments")
            st.json(user_entries)

            if st.button("💾 Save Deductions to DB"):
                success_count = 0
                for i, user in enumerate(user_entries):
                    if user.get("name") and user.get("email") and user.get("amount_paid"):
                        try:
                            db.deduct_amount(
                                user["name"],
                                user["email"],
                                int(float(user["amount_paid"]))
                            )
                            success_count += 1
                        except Exception as e:
                            st.error(f"❌ Failed to deduct for {user['name']}: {e}")
                    else:
                        st.warning(f"⚠️ Incomplete data for entry {i+1}, skipping.")
                st.success(f"✅ Deducted payments for {success_count} users.")
        else:
            st.error("❌ No valid user entries found.")