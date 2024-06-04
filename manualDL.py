import subprocess
import argparse
import os


def downloader(files_dir, link):
    # Check if the destination directory exists
    if not os.path.exists(files_dir):
        # Notify and create the directory if it does not exist
        print(f"Directory {files_dir} does not exist. Creating it...")
        os.makedirs(files_dir)
    
    # Proceed with the download
    subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", "-o", "%(title)s.%(ext)s", "--paths", files_dir, link])
    print(f"Downloaded {link} to {files_dir}")

def main():
    # 创建解析器
    parser = argparse.ArgumentParser()
    parser.add_argument("--link", type=str, required=True, help="youtube video or playlist link")
    parser.add_argument("--files_dir", type=str, required=True, help="files dir of the podcast")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    link = args.link
    files_dir = args.files_dir

    # 假设这些函数已经定义好
    downloader(files_dir, link)
    
if __name__ == "__main__":
    main()

