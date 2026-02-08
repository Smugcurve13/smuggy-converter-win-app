import shutil
import subprocess
import platform

def main():
	# Prefer shutil.which for a quick presence check
	if shutil.which("ffmpeg") is None:
		print("System Dependency - ffmpeg not present")
		resp = input("Attempt to install ffmpeg now? [Y/n]: ").strip().lower()
		if resp in ("", "y", "yes"):
			print("Attempting to install ffmpeg...")
			if platform.system() == "Windows":
				# Try winget (Windows 10/11)
				subprocess.run(["winget", "install", "--id", "Gyan.FFmpeg", "-e", "--source", "winget"], check=False)
			elif platform.system() == "Linux":
				# Use apt by default; user may need to run with sudo privileges
				subprocess.run(["sudo", "apt", "update"], check=False)
				subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg"], check=False)
			else:
				print("Automatic installation not supported on this platform. Please install ffmpeg manually.")
				return 1
		else:
			print("Installation cancelled by user")
			return 1
            

	# Verify ffmpeg is runnable
	try:
		result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
		# Print first line of version output (optional)
		first_line = result.stdout.splitlines()[0] if result.stdout else ""
		print(first_line or "ffmpeg present")
		return 0
	except (subprocess.CalledProcessError, FileNotFoundError):
		print("ffmpeg not present")
		return 1

if __name__ == "__main__":
	exit(main())