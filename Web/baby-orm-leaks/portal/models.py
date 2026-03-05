from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class EmployeeManager(BaseUserManager):
    def create_user(self, username, email, password, **extra):
        user = self.model(username=username, email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user


class Employee(AbstractBaseUser):
    """
    Custom user model for ShadowCorp employees.
    The `secret_token` field is internal and never exposed via the API.
    """
    ROLES = [
        ('employee', 'Employee'),
        ('manager',  'Manager'),
        ('admin',    'Administrator'),
    ]

    username     = models.CharField(max_length=64, unique=True)
    email        = models.EmailField(unique=True)
    full_name    = models.CharField(max_length=128)
    role         = models.CharField(max_length=32, choices=ROLES, default='employee')
    department   = models.CharField(max_length=64, default='')
    is_active    = models.BooleanField(default=True)
    date_joined  = models.DateTimeField(auto_now_add=True)

    # This field is NEVER returned by the API — but the ORM leak lets you read it
    secret_token = models.CharField(max_length=128, blank=True)

    objects = EmployeeManager()

    USERNAME_FIELD  = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'portal_employee'

    def __str__(self):
        return self.username

    # Fields returned by the /api/login endpoint
    @property
    def public_data(self):
        return {
            'id':         self.id,
            'username':   self.username,
            'email':      self.email,
            'full_name':  self.full_name,
            'role':       self.role,
            'department': self.department,
            'is_active':  self.is_active,
        }
