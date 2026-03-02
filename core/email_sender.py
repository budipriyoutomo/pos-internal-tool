# core/email_sender.py
import smtplib
from email.message import EmailMessage
from config.settings import settings 
import os

class EmailSender:
    def __init__(self):
        self.config = settings.get_mail_config()
    
    def send_report(self, subject, body, attachment_path):
        try:
            # Create message
            msg = EmailMessage()
            msg['From'] = self.config['sender']
            msg['To'] = self.config['receiver']
            if self.config['cc']:  # Tambah CC jika ada
                msg['CC'] = self.config['cc']
            msg['Subject'] = subject
            msg.set_content(body)
            
            # Ambil nama file dari path
            filename = os.path.basename(attachment_path)  # Ini akan ambil "OUTLET01_2023-08-25.txt"
            
            print(f"📎 Attachment filename: {filename}")
            
            # Add attachment dengan nama file asli
            with open(attachment_path, 'rb') as f:
                file_data = f.read()
                msg.add_attachment(
                    file_data,
                    maintype='text',
                    subtype='plain',
                    filename=filename  # Gunakan nama file asli
                )
            
            # Kirim email
            print(f"📧 Mengirim email ke {self.config['receiver']}...")
            
            # Tentukan penerima (To + CC)
            recipients = [self.config['receiver']]
            if self.config['cc']:
                recipients.append(self.config['cc'])
            
            # Kirim dengan SMTP_SSL
            with smtplib.SMTP_SSL(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.login(self.config['sender'], self.config['password'])
                server.send_message(msg, to_addrs=recipients)
            
            print(f"✅ Email terkirim! Attachment: {filename}")
            
        except Exception as e:
            print(f"❌ Gagal kirim email: {e}")
            raise