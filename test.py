from flask import Flask, flash, render_template, url_for, redirect, request
from flask_wtf import FlaskForm
from wtforms import SearchField, StringField, SubmitField,SelectField,SelectMultipleField,IntegerField,RadioField,widgets,BooleanField
from wtforms.validators import DataRequired
import sqlite3
import pandas as pd
import os
import allel
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
import subprocess