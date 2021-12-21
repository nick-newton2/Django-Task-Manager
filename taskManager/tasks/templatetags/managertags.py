from django import template

register = template.Library()

#Allows for multi-layered dictionary accesses in html templates (dict.task.id)
@register.simple_tag
def dict_get(dct, key):
    return dct.get(key)