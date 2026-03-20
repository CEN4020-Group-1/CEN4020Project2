from app import create_app

app = create_app()

# -----------------------------
# Run Server on http://127.0.0.1:5001
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5001)