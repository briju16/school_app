from fastapi import FastAPI, HTTPException, Body,Query
from pymongo import MongoClient
from pymongo.collection import Collection
from bson import ObjectId
import json
from fastapi import Path
from fastapi.responses import FileResponse
from fpdf import FPDF
from num2words import num2words
import qrcode

client = MongoClient('mongodb://localhost:27017')
db = client['UserDetails']
collection = db['Login_Authentication']

app = FastAPI()

def connect_to_mongodb(mongodb_uri):
    try:
        client = MongoClient(mongodb_uri)
        db = client.get_database()
        collection: Collection = db["Students_Table"]
        return client, collection

    except Exception as e:
        print("Error connecting to MongoDB:", e)
        return None, None

@app.get("/login/")  
async def login(username: str, password: str):
    user = collection.find_one({"username": username})

    if user is None or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful"}


@app.get("/students/")
def get_students():
    mongodb_uri = "mongodb://localhost:27017/Students_DB"
    client, collection = connect_to_mongodb(mongodb_uri)

    if client is not None and collection is not None:
        students = list(collection.find({}))
        students = json.loads(json.dumps(students, default=str))
        client.close()
        return students

    else:
         return {"message": "Failed to connect to MongoDB or the collection does not exist."}

   
@app.get("/students/{Admission_number}")
def get_student_by_admission_number(Admission_number: int = Path(..., description="Admission number of the student")):
    mongodb_uri = "mongodb://localhost:27017/Students_DB"
    client, collection = connect_to_mongodb(mongodb_uri)

    if client is not None and collection is not None:
        student = collection.find_one({"Admission_number": Admission_number})

        if student:
            student = json.loads(json.dumps(student, default=str))
            client.close()
            return student
        else:
            return {"message": "Student not found."}
    else:
        return {"message": "Failed to connect to MongoDB or the collection does not exist."}

   
@app.put("/students/update_individual/{Admission_number}")
def update_individual_by_admission_number(
    Admission_number: int = Path(..., description="Admission number of the student"),
    updated_student: dict = Body(...),):

    mongodb_uri = "mongodb://localhost:27017/Students_DB"
    client, collection = connect_to_mongodb(mongodb_uri)

    if client is not None and collection is not None:
        result = collection.update_one(
            {"Admission_number": Admission_number},
            {"$set": updated_student},)

        if result.modified_count > 0:
                updated_student = collection.find_one({"Admission_number": Admission_number})

                if updated_student:
                    updated_student = json.loads(json.dumps(updated_student, default=str))
                    client.close()
                    return updated_student

                else:
                    return {"message": "Updated student not found."}

        else:
            return {"message": "Student not found or no changes were made."}

    else:
        return {"message": "Failed to connect to MongoDB or the collection does not exist."}


@app.put("/insert_fee_student/")
def insert_fee_student(student_details: dict = Body(...)):
    mongodb_uri = "mongodb://localhost:27017"
    client = MongoClient(mongodb_uri)

    if client is not None:
        db = client["fee_db"]
        collection = db["fee_collection"]
        result = collection.insert_one(student_details)

        if result.inserted_id:
            inserted_student = collection.find_one({"_id": result.inserted_id})

            if inserted_student:
                inserted_student = json.loads(json.dumps(inserted_student, default=str))
                client.close()
                return inserted_student
            else:
                return {"message": "Inserted student not found."}
        else:
            return {"message": "Failed to insert student details."}
    else:
        return {"message": "Failed to connect to MongoDB."}

class PDF(FPDF):
    def header(self):
        self.set_fill_color(173, 216, 230)  
        self.rect(0, 0, self.w, self.h, 'F')  
        self.image('mnr.jpeg', 10, 6, 33)
        self.ln(60)
        self.set_font('Arial', 'B', 12)
        title = 'FEE RECEIPT'
        title_width = self.get_string_width(title)
        self.text((210 - title_width) / 2, 23, title)
        self.set_font('Arial', 'B', 10)
        school_name = 'MNR WORLD SCHOOL'
        school_name_width = self.get_string_width(school_name)
        self.text((210 - school_name_width) / 2, 30, school_name)

@app.get("/generate_receipt/")
async def generate_receipt(admission_number: str = Query(...)):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    client = MongoClient("mongodb://localhost:27017/")
    db = client["receipt_db"]
    collection = db["receipt_collection"]

    receipt_data = collection.find_one({"admission_number": admission_number})

    if receipt_data is None:
        client.close()
        raise HTTPException(status_code=404, detail="Receipt data not found")
    
    
    student_name = receipt_data["student_name"]
    admission_number = receipt_data["admission_number"]
    phone_no = receipt_data["phone_no"]
    transaction_id = receipt_data["transaction_id"]
    date = receipt_data["date"]
    time = receipt_data["time"]

    pdf.text(10, 43, f"Name: {student_name}")
    pdf.text(10, 53, f"Admission_number: {admission_number}")
    pdf.text(10, 63, f"Phone_number: {phone_no}")
    pdf.text(130, 43,f"Transaction_id: {transaction_id}")
    pdf.text(130, 53,f"Date: {date}")
    pdf.text(130, 63,f"Time: {time}")

    pdf.set_font("Arial", 'B', size=12)

    pdf.set_x(10)
    pdf.cell(30, 10, "Sl No.", 1, 0, 'C')
    pdf.cell(80, 10, "Particulars", 1, 0, 'C')
    pdf.cell(60, 10, "Amount", 1, 1, 'C')

    TotalFees = receipt_data["TotalFees"]
    PaidFees= receipt_data["PaidFees"]
    DueFees = receipt_data["DueFees"]    

    fees = [
        (f"TotalFees: ", TotalFees),
        (f"PaidFees: ", PaidFees),
        (f"DueFees: ", DueFees)
    ]

    sl_no = 1
    for fee in fees:
        description, amount = fee
        pdf.set_x(10)
        pdf.cell(30, 10, str(sl_no), 1)
        pdf.cell(80, 10, description, 1)
        pdf.cell(60, 10, f"{amount:.2f}", 1, 1, 'C')
        sl_no += 1

    amount_in_words = num2words(PaidFees, lang='en').replace('-', ' ').title()
    pdf.set_x(10)  
    pdf.cell(30, 10, "(In words:)", 1)
    pdf.cell(140, 10,f"{amount_in_words} rupees only", 1, 1, 'C')

    pdf.set_font("Arial", size=12)
    pdf.set_x(10)
    pdf.ln(10)

    payment_mode_mapping = {
    "Cash": "Cash",
    "Cheque": "Cheque",
    "Debit Card": "Debit Card",
    "Credit Card": "Credit Card"}

    payment_mode = receipt_data["payment_mode"]

    paid_by = payment_mode_mapping.get(payment_mode, "Unknown")

    payment_options = ["Paid by:", "Cash", "Cheque", "Debit Card", "Credit Card"]
    for option in payment_options:
        if option == paid_by:
            pdf.set_font("Arial", 'B', size=14)  
        else:
            pdf.set_font("Arial", size=14)
        pdf.cell(34, 10, option, 1, 0, 'C')

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        
        box_size=5,
        border=2,
    )
    qr.add_data("Your QR Code Data Here")  
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_path = "qrcode.png"
    img.save(img_path)  

    pdf.image(img_path, x=155, y=150, w=25)

    pdf.ln(55)
    pdf.set_font("Arial", 'I', size=12)
    pdf.text(10, pdf.get_y() + 20, "Signature of Center HOD")
    pdf.text(135, pdf.get_y() + 20, "Signature of Student")

    pdf.output("fee.pdf")

    client.close()
    return FileResponse("fee.pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
