import re
import os
from ffd.ffprobe import extract_info


def rmAdSegment(dest, logger):
    indexFilePath = os.path.join(dest, 'index.m3u8')
    adPath = os.path.join(dest, 'index.ad.m3u8')
    return check_m3u8_file(index_path=indexFilePath, ad_path=adPath, logger=logger)

def check_m3u8_file(index_path, ad_path, logger):
    ad_content = ['#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-PLAYLIST-TYPE:VOD\n#EXT-X-MEDIA-SEQUENCE:0\n']
    unique_infos = set()

    with open(index_path, 'r') as f:
        content = f.read()

    key_match = re.findall(r'#EXT-X-KEY.*URI="(.+?)"', content)
    if key_match:
        raise RuntimeError('Exist key encryption. cannot extract ts info')

    base_info = set()
    failed_count = []
    def tsMap(match):
        ts_path = match.group(5).strip()
        ext_x_key_mth = match.group(2) or ''

        full_path = os.path.join(os.path.dirname(index_path), ts_path)
        video_info = get_video_info(full_path, logger)

        if video_info:
            if video_info['codec'] == 'png':
                raise RuntimeError('it could be a stream masqueraded with a PNG header. Try to fix them.')
            info_str = f"{video_info['codec']}_{video_info['codec_profile']}_{video_info['width']}x{video_info['height']}_{video_info['framerate']}_{video_info['codec_long_name']}"
            if not len(base_info):
                base_info.add(info_str)
                logger.info(info_str)
            if info_str not in base_info:
                unique_infos.add(ts_path)

                # logger.info(f"TS File: {ts_path}")
                # logger.info("Video Codec:", video_info['codec'])
                # logger.info("Video Codec Profile:", video_info['codec_profile'])
                # logger.info("Resolution:", f"{video_info['width']}x{video_info['height']}")
                # logger.info("Framerate:", video_info['framerate'])
                # logger.info("codec_long_name :", video_info['codec_long_name'])
                # logger.info("\n" + "=" * 30 + "\n")

                ad_content.append(match.group(1) + ext_x_key_mth + match.group(3) + ts_path + '\n')
                return ''
            return match.group(3) + ts_path + '\n'
        else:
            failed_count.append(None)
        if len(failed_count) > 2:
            raise RuntimeError('give up after more than 2 failures')

    content = re.sub(r'((?:#EXT-X-DISCONTINUITY\n)*)(#EXT-X-KEY:METHOD=NONE\n)?(#EXTINF:.+?\n)(#EXT-X-PRIVINF:.+\n)?(.+)\n', tsMap, content)
    ad_content.append('#EXT-X-ENDLIST')
    ad_ctn = ''.join(ad_content)

    if unique_infos:
        logger.info("=ad segment" + "=" * 30)
        for unique in unique_infos:
            logger.info(unique)
        with open(index_path, 'w') as f:
            f.write(content)

        with open(ad_path, 'w') as f:
            f.write(ad_ctn)
        logger.info('write m3u8 file... remove ad complete')
    else:
        logger.info("No discontinuity segment found.")
    return unique_infos

def get_video_info(file_path, logger):
    info = extract_info(url=file_path, logger=logger)
    if info:
        return {
            'codec': info['v_codec_name'],
            'codec_profile': info['v_profile'],
            'width': info['v_width'],
            'height': info['v_height'],
            'framerate': info['v_avg_frame_rate'],
            'codec_long_name': info['v_codec_long_name']
        }
    else:
        return None

