from django.contrib import admin
from django.contrib import messages
from django import forms
from django.shortcuts import render
from django.utils.html import format_html
from .models import Product, Station, ProductMedia, Linewise

class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ('file',  'duration', 'is_selected', 'is_active')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')
    inlines = [ProductMediaInline]

    
class SelectedMediaInline(admin.TabularInline):
    model = Station.selected_media.through
    extra = 1
    verbose_name = "Selected Media"
    verbose_name_plural = "Selected Media"

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('name', 'manager', 'get_selected_media_count')
    search_fields = ('name', 'manager__username')
    filter_horizontal = ('products', 'selected_media')
    inlines = [SelectedMediaInline]
    actions = ['select_product_for_stations']

    def get_selected_media_count(self, obj):
        return obj.selected_media.count()
    get_selected_media_count.short_description = 'Selected Media Count'

    @admin.action(description="Select product for stations")
    def select_product_for_stations(self, request, queryset):
        class ProductSelectionForm(forms.Form):
            _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
            product = forms.ModelChoiceField(queryset=Product.objects.all())

        form = None
        if 'apply' in request.POST:
            form = ProductSelectionForm(request.POST)
            if form.is_valid():
                product = form.cleaned_data['product']
                count = 0
                for station in queryset:
                    station.products.add(product)
                    media = ProductMedia.objects.filter(product=product, station=station, is_active=True)
                    station.selected_media.set(media)
                    media.update(is_selected=True)
                    count += 1
                self.message_user(request, f"Product {product} has been added to {count} stations and media updated.", messages.SUCCESS)
                return None

        if not form:
            form = ProductSelectionForm(initial={'_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME)})

        return render(request, 'admin/select_product_intermediate.html', {'form': form, 'stations': queryset})

class ProductMediaAdminForm(forms.ModelForm):
    class Meta:
        model = ProductMedia
        fields = '__all__'

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            ext = file.name.split('.')[-1].lower()
            if ext not in ['pdf', 'mp4', 'mov', 'zip', 'jpg', 'jpeg', 'png', 'gif']:
                raise ValidationError("File extension not allowed. Allowed extensions are: pdf, mp4, mov, zip, jpg, jpeg, png, gif.")
        return file

@admin.register(ProductMedia)
class ProductMediaAdmin(admin.ModelAdmin):
    form = ProductMediaAdminForm
    list_display = ('product', 'station', 'file_display', 'duration', 'is_selected', 'is_active')
    list_filter = ('product', 'station', 'is_selected', 'is_active')
    search_fields = ('product__name', 'product__code', 'station__name')
    
    def file_display(self, obj):
        if obj.file:
            file_name = obj.file.name.lower()
            if file_name.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                return format_html('<a href="{}" target="_blank"><img src="{}" width="50" height="50" /></a>', 
                                 obj.file.url, obj.file.url)
            elif file_name.endswith('.pdf'):
                return format_html('<a href="{}" target="_blank">PDF: {}</a>', 
                                 obj.file.url, obj.file.name.split('/')[-1])
            elif file_name.endswith(('.mp4', '.mov')):
                return format_html('<a href="{}" target="_blank">Video: {}</a>', 
                                 obj.file.url, obj.file.name.split('/')[-1])
            else:
                return format_html('<a href="{}" target="_blank">{}</a>', 
                                 obj.file.url, obj.file.name.split('/')[-1])
        return "-"
    file_display.short_description = "File"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.file and obj.file.name.endswith('.zip'):
            messages.success(request, f"ZIP file '{obj.file.name}' has been processed and individual files have been added.")

class LinewiseAdminForm(forms.ModelForm):
    class Meta:
        model = Linewise
        fields = '__all__'

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            if instance.product:
                instance.update_stations_and_media()
        return instance

@admin.register(Linewise)
class LinewiseAdmin(admin.ModelAdmin):
    form = LinewiseAdminForm
    list_display = ('name', 'product', 'get_stations')
    search_fields = ('name', 'product__name', 'stations__name')
    autocomplete_fields = ['product']
    filter_horizontal = ('stations',)

    def get_stations(self, obj):
        return ", ".join([station.name for station in obj.stations.all()])
    get_stations.short_description = 'Stations'