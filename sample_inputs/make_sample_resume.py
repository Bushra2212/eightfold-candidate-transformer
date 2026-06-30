from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("sample_inputs/resume_sample.pdf", pagesize=letter)
c.setFont("Helvetica-Bold", 14)
c.drawString(72, 750, "Bushra Khan")
c.setFont("Helvetica", 10)
c.drawString(72, 735, "Email: bushra.khan@example.com | Phone: +91 9876543210")
c.drawString(72, 720, "Location: Hyderabad, Telangana, India")

c.setFont("Helvetica-Bold", 11)
c.drawString(72, 695, "Summary")
c.setFont("Helvetica", 10)
c.drawString(72, 680, "Software Engineer with 4 years of experience in backend systems and APIs.")

c.setFont("Helvetica-Bold", 11)
c.drawString(72, 655, "Experience")
c.setFont("Helvetica", 10)
c.drawString(72, 640, "Software Engineer, TechCorp, Jan 2022 - Present")
c.drawString(72, 625, "Backend Developer, StartupX, Jun 2020 - Dec 2021")

c.setFont("Helvetica-Bold", 11)
c.drawString(72, 600, "Skills")
c.setFont("Helvetica", 10)
c.drawString(72, 585, "Python, JavaScript, SQL, AWS, Docker")

c.save()
print("Sample resume created.")