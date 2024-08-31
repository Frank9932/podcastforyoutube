import json
from src.utlis import (create_rss_file, remove_temp_files)
from src.downloader import download_audios
from src.cloudflare_s3 import get_bucket, upload_files, delete_files
from src.database import initialize_database, fetch_metadata, insert_metadata


def main():
    db_path = './database.db'
    conn = initialize_database(db_path)

    # load config
    with open('./config/channels.json', 'r') as channels:
        channels = json.load(channels)
    with open('./config/settings.json', 'r') as settings:
        settings = json.load(settings)

    web_dir = settings['bucket']['bucket_url']
    temp_dir = './temp/'

    # download
    new_metadata_list = download_audios(channels,temp_dir)

    # rss & database
    metadata_list = fetch_metadata(conn)
    
    metadata_list.extend(new_metadata_list)
    valid_episodes = create_rss_file(channels, metadata_list, temp_dir, web_dir)

    insert_metadata(conn, new_metadata_list)

    # handle cloud files
    invalid_episodes = [episode for episode in metadata_list if episode not in valid_episodes]
    bucket = get_bucket(settings)
    upload_files(temp_dir, bucket)
    delete_files(invalid_episodes, bucket)

    # removal
    remove_temp_files(temp_dir)

    conn.close()

if __name__ == '__main__':
    main()