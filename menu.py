# -*- coding: UTF-8 -*-
import tabtabtab

m_edit = nuke.menu('Nuke').findItem('Edit')
m_edit.addCommand('Tabtabtab', tabtabtab.main, 'Tab')