from django.db import migrations, connection

def enable_pg_trgm(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_farmerprofile_idx_farm_name"),  # Update this with your latest migration file
    ]

    operations = [
        migrations.RunPython(enable_pg_trgm),
    ]
