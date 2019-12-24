import smtplib
 
sender_email = "w4686112x0418@gmail.com"
rec_email = "w4686112x0418@gmail.com"
password = input(str("Please enter your password : "))

message = "Hey, this was sent using python"
 
server = smtplib.SMTP('smtp.gmail.com', 25)
server.starttls()
server.login(sender_email, password)
print("Login success")
server.sendmail(sender_email, rec_email, message)
print("Email has been sent to ", rec_email)