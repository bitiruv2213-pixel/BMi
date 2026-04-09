from django import template
import re

register = template.Library()

@register.filter
def youtube_embed(url):
    '''YouTube URL ni embed formatga o'zgartirish'''
    if not url:
        return ''
    
    # youtu.be format
    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
    if match:
        return f'https://www.youtube.com/embed/{match.group(1)}'
    
    # youtube.com format
    match = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', url)
    if match:
        return f'https://www.youtube.com/embed/{match.group(1)}'
    
    # Already embed format
    if 'youtube.com/embed/' in url:
        return url
    
    return url


@register.filter
def vimeo_embed(url):
    '''Vimeo URL ni embed formatga o'zgartirish'''
    if not url:
        return ''
    
    match = re.search(r'vimeo\.com/(\d+)', url)
    if match:
        return f'https://player.vimeo.com/video/{match.group(1)}'
    
    return url


@register.filter
def video_duration(minutes):
    '''Daqiqalarni soat:daqiqa formatga o'zgartirish'''
    if not minutes:
        return '0:00'
    
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0:
        return f'{hours}:{mins:02d}'
    return f'{mins}:00'
