from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from .models import Station, ProductMedia
import json
import time
import os

def get_file_extension(file_path):
    """Helper function to get the clean file extension from a file path"""
    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    # Map image extensions to common type
    if ext in ['jpg', 'jpeg', 'png', 'gif']:
        return ext
    return ext

def get_station_media(request, station_id):
    station = get_object_or_404(Station, pk=station_id)
    selected_media = ProductMedia.objects.filter(
        station=station,
        is_selected=True,
        is_active=True
    )
    
    media_data = [
        {
            'id': m.id,
            'url': m.file.url,
            'type': get_file_extension(m.file.name),
            'duration': m.duration,
            'product_name': m.product.name,
            'product_code': m.product.code
        }
        for m in selected_media
    ]
    return JsonResponse({'media': media_data})

def station_media_slider(request, station_id):
    station = get_object_or_404(Station, pk=station_id)
    selected_media = ProductMedia.objects.filter(
        station=station,
        is_selected=True,
        is_active=True
    )
    return render(request, 'station_slider.html', {'station': station, 'selected_media': selected_media})

def station_media_stream(request, station_id):
    def event_stream():
        last_update = None
        while True:
            station = Station.objects.get(pk=station_id)
            selected_media = ProductMedia.objects.filter(
                station=station,
                is_selected=True,
                is_active=True
            ).select_related('product')
            
            # Convert QuerySet to list of dicts for comparison
            current_media = list(selected_media.values(
                'id', 'file', 'duration', 'product__name', 'product__code'
            ))
            
            # Only send update if media has changed
            if current_media != last_update:
                media_data = {
                    'media': [
                        {
                            'id': m.id,
                            'url': m.file.url,
                            'type': get_file_extension(m.file.name),
                            'duration': m.duration,
                            'product_name': m.product.name,
                            'product_code': m.product.code
                        }
                        for m in selected_media
                    ],
                    'screen_name': station.screen_name
                }
                last_update = current_media
                yield f"data: {json.dumps(media_data)}\n\n"
            
            time.sleep(10)  # Check for updates every 10 seconds

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable buffering for nginx
    return response