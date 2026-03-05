from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password',     models.CharField(max_length=128, verbose_name='password')),
                ('last_login',   models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('username',     models.CharField(max_length=64, unique=True)),
                ('email',        models.EmailField(max_length=254, unique=True)),
                ('full_name',    models.CharField(max_length=128)),
                ('role',         models.CharField(choices=[('employee','Employee'),('manager','Manager'),('admin','Administrator')], default='employee', max_length=32)),
                ('department',   models.CharField(default='', max_length=64)),
                ('is_active',    models.BooleanField(default=True)),
                ('date_joined',  models.DateTimeField(auto_now_add=True)),
                ('secret_token', models.CharField(blank=True, max_length=128)),
            ],
            options={'db_table': 'portal_employee'},
        ),
    ]
