import json
import re
import subprocess
import os


meta_structure = {
    'v_codec_name': '',
    'v_codec_long_name': '',
    'v_profile': '',
    'v_bit_rate': 0,
    'v_avg_frame_rate': '',
    'v_width': 0,
    'v_height': 0,
    'v_duration': 0,
    'a_codec_name': '',
    'a_codec_long_name': '',
    'a_profile': '',
    'a_bit_rate': 0,
    'a_sample_rate': 0,
    'a_channels': 0,
    'a_duration': 0,
}

def get_ffprobe_data(url, logger):
    cmd = ['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-i', url]
    if url.endswith('m3u8'):
        cmd.extend(['-allowed_extensions', 'ALL'])
    if url.startswith('http'):
        cmd.extend(['-timeout', '5000000', '-rw_timeout', '5000000'])
    logger.info('execute: ' + ' '.join(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    max_pull_ts = 10
    with process.stderr:
        for stderr_line in iter(process.stderr.readline, ''):
            err_msg = stderr_line.strip('\n')
            if 'Error in the pull function' in err_msg:
                max_pull_ts -= 1
                if max_pull_ts == 0:
                    logger.error('Exceeded the maximum number of retries 10')
                    process.kill()
            logger.error(err_msg)
    stdout_lines = []
    with process.stdout:
        for stdout_line in iter(process.stdout.readline, ""):
            stdout_lines.append(stdout_line)
    process.wait()
    if process.returncode == 0:
        return json.loads(''.join(stdout_lines))
    else:
        return False

def extract_info(url, va_format=True, logger=None):
    try:
        data = get_ffprobe_data(url, logger)
        if not data:
            raise Exception(f'ffprobe output error')
        if va_format:
            info = extract_streams(data)
            # if re.match(r'^\/(?!.*(m3u8|ts)$).*$', url) and os.path.exists(url):
            #     size, unit = convert_bytes(os.path.getsize(url))
            #     info['file_size'] = f'{size:.2f}{unit}'
        else:
            info = data
        return info
    except Exception as e:
        if 'output error' in str(e):
            logger.error(e)
        else:
            logger.exception(e)
        return False

def extract_streams(data):
    meta = meta_structure.copy()
    for key, val in meta.items():
        stm_key = re.sub(r'^(a|v)_', '', key)
        for stream in data['streams']:
            if (
                (stream.get('codec_type') == 'video' and key.startswith('v_'))
                or (stream.get('codec_type') == 'audio' and key.startswith('a_'))
                ):
                meta[key] = stream.get(stm_key)
            else:
                pass

    meta['lang'] = extract_audio_language(data)
    return meta

def extract_audio_language(data):
    languages = []
    for stream in data['streams']:
        if stream['codec_type'] == 'audio' and 'tags' in stream and 'language' in stream['tags']:
            languages.append(stream['tags']['language'])
    return ','.join(languages)
