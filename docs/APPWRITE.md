# Appwrite migration status

Project: `6ac46d45002b91afdd73`; endpoint: `https://sgp.cloud.appwrite.io/v1`.
The server reads `APPWRITE_API_KEY` from its environment. Never put this key in Android, source control or chat.

`python backend/scripts/check_appwrite.py` performs a read-only database-list request. It requires `databases.read` and does not create resources or migrate data. Run it after the next planned Codespaces restart; no restart is needed for each individual setup step.

SQLite is still the active database. Appwrite is not a SQLAlchemy SQLite replacement. Moving production requires an Appwrite data model, authentication and authorization integration, private file storage, deployed functions for hashing and provider calls, and migration/rollback checks. Codespaces remains development infrastructure until those services are deployed and verified.

The current backend key scopes are databases.read, tables.read, rows.read, rows.write, files.read and files.write. Database/table/bucket creation is a separate console setup task; this key cannot create their structure. Function deployments require their own appropriate deployment credentials.

Appwrite Education currently lasts six months: https://appwrite.io/education . Plan for expiry before commercial launch. Creating the project or adding its key does not make Ditto commercially ready.
