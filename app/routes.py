from flask import Blueprint, redirect, url_for, Flask, jsonify, render_template, flash, render_template_string, request,g, session

main = Blueprint('main', __name__)

@main.route('/')
def index():
    
    return render_template('index.html')
