# Secrets

Do not paste retailer credentials into chat and do not commit them to Git.

## Local development

Create a local `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Then fill in only the credentials you need:

```env
PRICESMART_USERNAME=your-test-account@example.com
PRICESMART_PASSWORD=your-test-account-password

JTA_USERNAME=your-test-account@example.com
JTA_PASSWORD=your-test-account-password
```

Use dedicated test accounts where possible:
- unique password
- no saved payment method
- no sensitive personal data
- rotate password if needed

## Production

Use deployment secrets rather than committed files:
- GitHub Actions secrets for CI/CD
- VPS `.env` file with restricted permissions
- a managed secret store later if needed

The scraper reads credentials through `apps/api/app/scraping_credentials.py`.
