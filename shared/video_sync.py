import os
import subprocess
import math
from PIL import Image
from shared.logger import get_logger

logger = get_logger("VideoSync")

def get_video_duration(video_path):
    try:
        cmd = ["ffmpeg", "-i", video_path]
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        for line in result.stderr.split('\n'):
            if "Duration:" in line:
                time_str = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = time_str.split(':')
                return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception as e:
        logger.error(f"Failed to get video duration: {e}")
    return 0.0

def find_audio_match(short_video_path, long_video_path, temp_dir):
    """
    Extracts audio from both videos, downsamples to 8kHz mono, and uses cross-correlation
    to find the exact millisecond offset where they perfectly align.
    Returns (best_offset_seconds, confidence_score).
    """
    try:
        from scipy.io import wavfile
        from scipy import signal
        import numpy as np
    except ImportError:
        logger.warning("scipy or numpy not installed. Skipping audio sync.")
        return 0, 0

    os.makedirs(temp_dir, exist_ok=True)
    short_wav = os.path.join(temp_dir, "short.wav")
    long_wav = os.path.join(temp_dir, "long.wav")
    
    # Extract audio (8kHz mono for speed)
    subprocess.run(["ffmpeg", "-y", "-i", short_video_path, "-ac", "1", "-ar", "8000", short_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["ffmpeg", "-y", "-i", long_video_path, "-ac", "1", "-ar", "8000", long_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if not os.path.exists(short_wav) or not os.path.exists(long_wav):
        return 0, 0
        
    try:
        sr_short, data_short = wavfile.read(short_wav)
        sr_long, data_long = wavfile.read(long_wav)
        
        # Normalize and convert to float32
        data_short = data_short.astype(np.float32) / np.max(np.abs(data_short) + 1e-6)
        data_long = data_long.astype(np.float32) / np.max(np.abs(data_long) + 1e-6)
        
        # If long audio is actually shorter than short audio due to clipping, fail safely
        if len(data_long) < len(data_short):
            return 0, 0
            
        # Cross correlation
        correlation = signal.correlate(data_long, data_short, mode='valid')
        
        best_idx = np.argmax(correlation)
        best_offset = best_idx / sr_long
        
        # Calculate a Signal-to-Noise Ratio (SNR) style confidence score
        peak = correlation[best_idx]
        mean_corr = np.mean(np.abs(correlation))
        confidence = peak / (mean_corr + 1e-6)
        
        return best_offset, confidence
        
    except Exception as e:
        logger.error(f"Audio sync failed: {e}")
        return 0, 0
    finally:
        if os.path.exists(short_wav): os.remove(short_wav)
        if os.path.exists(long_wav): os.remove(long_wav)

def extract_motion_signature(video_path, temp_dir, prefix):
    os.makedirs(temp_dir, exist_ok=True)
    # Extract 1 frame per second, squashed to 16x16 to ignore minor layout differences
    cmd = [
        "ffmpeg", "-y", "-i", video_path, 
        "-vf", "fps=1,scale=16:16,format=gray", 
        os.path.join(temp_dir, f"{prefix}_%04d.jpg")
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    files = sorted([f for f in os.listdir(temp_dir) if f.startswith(prefix) and f.endswith(".jpg")])
    
    frames = []
    for f in files:
        filepath = os.path.join(temp_dir, f)
        frames.append(list(Image.open(filepath).convert('L').getdata()))
        os.remove(filepath)
        
    motion = []
    for i in range(1, len(frames)):
        diff = sum(abs(a - b) for a, b in zip(frames[i], frames[i-1]))
        motion.append(diff)
        
    if len(motion) == 0: 
        return []
        
    mean = sum(motion) / len(motion)
    variance = sum((x - mean)**2 for x in motion) / len(motion)
    std = math.sqrt(variance) if variance > 0 else 1
    
    return [(x - mean) / std for x in motion]

def find_motion_match(short_video_path, long_video_path, temp_dir):
    short_sig = extract_motion_signature(short_video_path, temp_dir, "short")
    long_sig = extract_motion_signature(long_video_path, temp_dir, "long")
    
    if not short_sig or not long_sig or len(short_sig) > len(long_sig):
        return 0, 0
        
    best_offset = 0
    max_corr = -float('inf')
    
    for offset in range(len(long_sig) - len(short_sig) + 1):
        corr = sum(a * b for a, b in zip(short_sig, long_sig[offset:offset+len(short_sig)]))
        # Pseudo-pearson score since they are standardized
        score = corr / len(short_sig)
        if score > max_corr:
            max_corr = score
            best_offset = offset
            
    return best_offset, max_corr

def find_clip_timestamps(short_video_path, long_video_path, temp_dir):
    """
    Returns (start_time_seconds, end_time_seconds) if a confident match is found.
    Returns (-1, -1) if no confident match is found.
    """
    logger.info("Attempting AUDIO fingerprint sync (high precision)...")
    audio_offset, audio_conf = find_audio_match(short_video_path, long_video_path, temp_dir)
    duration = get_video_duration(short_video_path)
    
    # SNR > 15 is usually a strong deterministic audio match
    if audio_conf > 15:
        logger.info(f"✅ Audio match found! Offset: {audio_offset:.2f}s (Confidence: {audio_conf:.1f})")
        return audio_offset, audio_offset + duration
        
    logger.warning(f"Audio match confidence too low ({audio_conf:.1f}). Falling back to MOTION sync...")
    motion_offset, motion_conf = find_motion_match(short_video_path, long_video_path, temp_dir)
    
    # Correlation > 0.85 is a strong visual match
    if motion_conf > 0.85:
        logger.info(f"✅ Visual motion match found! Offset: {motion_offset}s (Confidence: {motion_conf:.2f})")
        return motion_offset, motion_offset + duration
        
    logger.error(f"❌ Failed to find confident match. Audio Conf: {audio_conf:.1f}, Visual Conf: {motion_conf:.2f}")
    return -1, -1
