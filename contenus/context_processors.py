from .models import Theme, Devoir

def themes_nav(request):
    return {
        'themes_nav': Theme.objects.all(),
        'types_devoir_nav': Devoir.TypeDevoir.choices,
    }