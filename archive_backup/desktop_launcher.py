import subprocess
import sys

def main():
    print("Running MWE Engine Desktop App")
    print("1. Process a File")
    print("2. Process a Folder")
    print("3. Launch Interactive Web Viewer")
    choice = input("Enter choice (1/2/3): ").strip()

    if choice == "1":
        filepath = input("Enter path to .txt file: ").strip()
        subprocess.run([sys.executable, "main.py", "--file", filepath])
    elif choice == "2":
        folder = input("Enter path to folder with .txt files: ").strip()
        subprocess.run([sys.executable, "main.py", "--folder", folder])
    elif choice == "3":
        subprocess.run(["streamlit", "run", "streamlit_app.py"])
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()
