#! /usr/bin/env python3

from flask import render_template
from flask_admin.form.rules import HTML, BaseRule

from jinja2 import Markup

class UnvalidatedList(HTML):

    def __init__(self, field_name, linked_view, *args, **kwargs):
        self.field_name = field_name
        self.linked_view = linked_view
        super().__init__(self, *args, **kwargs)

    def __call__(self, form, *args, **kwargs):
        obj_list = getattr(form, self.field_name).object_data
        unval = [obj for obj in obj_list if not obj.validated]
        if not unval:
            return ''
        return Markup(render_template('unvalidated_list.html', unvalidated_list=unval, linked_view=self.linked_view))

class ViewButton(BaseRule):
    def __call__(self, form, *args, **kwargs):
        return Markup(render_template('view_button.html', instance_id=form._obj.id))

