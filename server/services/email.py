import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import get_settings

settings = get_settings()


async def send_email(subject: str, body: str):
    """Send email notification"""
    message = MIMEMultipart()
    message["From"] = settings.smtp_user
    message["To"] = settings.notification_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


async def send_commit_notification(repo: str, commit_message: str, status: str, error: str = None):
    """Send notification for a commit"""
    if status == "completed":
        subject = f"✅ Commit Success: {repo}"
        body = f"""
        <h2>Commit Pushed Successfully</h2>
        <p><strong>Repository:</strong> {repo}</p>
        <p><strong>Message:</strong> {commit_message}</p>
        """
    elif status == "skipped":
        subject = f"⚠️ Commit Skipped: {repo}"
        body = f"""
        <h2>Commit Skipped</h2>
        <p><strong>Repository:</strong> {repo}</p>
        <p><strong>Message:</strong> {commit_message}</p>
        <p><strong>Reason:</strong> Files not found in zip</p>
        """
    else:
        subject = f"❌ Commit Failed: {repo}"
        body = f"""
        <h2>Commit Failed</h2>
        <p><strong>Repository:</strong> {repo}</p>
        <p><strong>Message:</strong> {commit_message}</p>
        <p><strong>Error:</strong> {error or 'Unknown error'}</p>
        """
    
    await send_email(subject, body)


async def send_job_complete_notification(repo: str, total: int, completed: int, status: str):
    """Send notification when job completes"""
    if status == "completed":
        subject = f"🎉 Job Complete: {repo}"
        body = f"""
        <h2>All Commits Pushed!</h2>
        <p><strong>Repository:</strong> {repo}</p>
        <p><strong>Total Commits:</strong> {total}</p>
        <p><strong>Completed:</strong> {completed}</p>
        """
    elif status == "cancelled":
        subject = f"🛑 Job Cancelled: {repo}"
        body = f"""
        <h2>Job Cancelled</h2>
        <p><strong>Repository:</strong> {repo}</p>
        <p><strong>Total Commits:</strong> {total}</p>
        <p><strong>Completed before cancel:</strong> {completed}</p>
        """
    else:
        subject = f"❌ Job Failed: {repo}"
        body = f"""
        <h2>Job Failed</h2>
        <p><strong>Repository:</strong> {repo}</p>
        <p><strong>Total Commits:</strong> {total}</p>
        <p><strong>Completed before failure:</strong> {completed}</p>
        """
    
    await send_email(subject, body)
