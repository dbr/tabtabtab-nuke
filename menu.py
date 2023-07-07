# -*- coding: UTF-8 -*-
import nuke

if nuke.NUKE_VERSION_MAJOR < 11:
    import tabtabtab

    WINDOW_CONTEXT = 0
    APPLICATION_CONTEXT = 1
    DAG_CONTEXT = 2

    m_edit = nuke.menu('Nuke').findItem('Edit')
    m_edit.addCommand('Tabtabtab', tabtabtab.main, 'Tab', shortcutContext=DAG_CONTEXT)
