#!/usr/bin/env python
# -*- coding: utf8 -*-

import os
import os.path
import shutil
import sys
import traceback

import Image

import pygtk
pygtk.require20()
import gtk
import gobject

class ImageResizer(object):
    def __init__(self):
        builder = gtk.Builder()
        install_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        window_path = os.path.join(install_dir, 'Resources', 'mainWindow.glade')
        builder.add_from_file(window_path)
        
        signals = { 'on_input_dir_chooser_current_folder_changed': self.on_input_dir_chooser_current_folder_changed,
                    'on_height_rb_toggled' : lambda widget: self.on_radiobutton_changed('height_rb', widget.get_active()),
                    'on_width_rb_toggled' : lambda widget: self.on_radiobutton_changed('width_rb', widget.get_active()),
                    'on_percentual_rb_toggled' : lambda widget: self.on_radiobutton_changed('percentual_rb', widget.get_active()),
                    'on_ratio_rb_toggled' : lambda widget: self.on_radiobutton_changed('ratio_rb', widget.get_active()),
                    'on_process_btn_clicked': self.on_process_btn_clicked,
                    'on_size_txt_focus_out_event': self.on_size_txt_focus_out_event,
                    'on_resize_smaller_chb_toggled': self.on_resize_smaller_chb_toggled,
                    'on_main_window_delete_event': gtk.main_quit}
        builder.connect_signals(signals)
        
        self.main_window = builder.get_object('main_window')
        self.size_txt = builder.get_object('size_txt')
        self.unit_label = builder.get_object('unit_label')
        
        # inicializace adresare
        builder.get_object('input_dir_chooser').set_current_folder(os.path.expanduser('~'))
        # inicializace vnitrnich fieldu
        self.dimension = 'h'
        self.resize_smaller = False
        
        self.main_window.show_all()
    
    def main(self):
        gtk.main()
    
    def on_input_dir_chooser_current_folder_changed(self, widget, data = None):
        path = widget.get_filename()
        
        if not path:
            return
        
        path = path.decode('utf8')
        
        if not os.path.exists(path):
            self.show_error_dialog('Vybraná cesta neexistuje!')
            return
        if not os.access(path, os.X_OK | os.W_OK):
            self.show_error_dialog('Vybraná cesta není přístupná!')
            return
        
        self.path = path
    
    def on_radiobutton_changed(self, widget_id, toggled, data = None):
        if not toggled:
            return
        
        if widget_id in ('height_rb', 'width_rb'):
            self.unit_label.set_text('px')
            self.dimension = 'w' if widget_id == 'width_rb' else 'h' 
        elif widget_id == 'percentual_rb':
            self.unit_label.set_text('%')
            self.dimension = 'p'
        elif widget_id == 'ratio_rb':
            self.unit_label.set_text('')
            self.dimension = 'r'
    
    def on_resize_smaller_chb_toggled(self, widget, data = None):
        self.resize_smaller = widget.get_active()
    
    def on_size_txt_focus_out_event(self, widget, data = None):
        text = widget.get_text()
        if not text.isdigit() and self.dimension != 'r':
            text = ''.join([x for x in text if x.isdigit()])
            widget.set_text(text)
    
    def on_process_btn_clicked(self, widget, data = None):
        if not hasattr(self, 'path') or self.path == None or self.path == '':
            self.show_error_dialog('Vyberte cestu!')
            return

        text = self.size_txt.get_text()
        if text == None or text == '':
            self.show_error_dialog('Zadejte rozměr!')
            return
        
        if self.dimension != 'r':
            try:
                self.size = float(text)
            except:
                self.show_error_dialog('Zadaný rozměr nelze převést na desetinné číslo')
                return
        else:
            try:
                self.size = map(float,map(str.strip, text.split('x')))
            except:
                self.show_error_dialog('Zadaný řetězec nelze převést na poměr s desetinnými čísly')
        
        self.main_window.set_sensitive(False)
        try:
        	# TODO: multiprocessing - zparalelizovat process_file
     		# TODO: a taky pridat vypisovani do souboru, pri vice procesech by se chyba rychle ztratila
            self.walk_path(self.path) # TODO: nahradit os.path.walk
            self.show_info_dialog('Proces řádně ukončen.')
        except BaseException as err:
            self.show_error_dialog('Zachycena neošetřená výjimka!')
            print 'Unhandled exception: ' + str(err) + '\n'
            traceback.print_exc()
        finally:
            self.main_window.set_sensitive(True)
        
    def walk_path(self, path):
        for file in os.listdir(path):
            filepath = os.path.join(path, file)
            if os.path.isdir(filepath):
                self.walk_path(filepath)
            else:
                self.process_file(filepath)
    
    def process_file(self, path):
        if path.upper().endswith('.BAK'):
            return
        
        try:
            im = Image.open(path)
        except Exception as err:
            print 'Exception when loading file ' + path +':'
            print '"' + str(err) + '"\n'
            return # soubor nejspis neni obrazek
        
        print 'File %s loaded\n' % path
        
        # neni-li nastaven priznak resize_smaller, obrazky mensi nez je novy
        # rozmer neupravuji
        if ((self.dimension == 'w' and im.size[0] <= self.size) \
            or (self.dimension == 'h' and im.size[1] <= self.size) \
            or (self.dimension == 'p' and self.size >= 100)) \
            and self.resize_smaller == False:
            print '\tFile is too small, skipping\n'
            return
        
        bak_path = path + '.BAK'
        if os.path.exists(bak_path):
            os.remove(bak_path)
        shutil.copyfile(path, bak_path)
        print '\tBackup created\n'
        
        print '\tOriginal size = ' + str(im.size) + ' px\n'
        
        if self.dimension != 'r':
            im = self.resize_image_base(im)
        else:
            im = self.resize_image_with_ratio(im)
        
        im.save(path)
        
        print '\tFile updated\n'
    
    def show_error_dialog(self, message):
        md = gtk.MessageDialog(self.main_window, 
            gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, 
            gtk.BUTTONS_CLOSE, message)
        md.run()
        md.hide()
        md.destroy()
    
    def show_info_dialog(self, message):
        md = gtk.MessageDialog(self.main_window, 
            gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, 
            gtk.BUTTONS_CLOSE, message)
        md.run()
        md.hide()
        md.destroy()
    
    def resize_image_base(self, im):
        if self.dimension == 'p':
            rate = self.size / 100
        elif self.dimension == 'w':
            rate = self.size / im.size[0]
        elif self.dimension == 'h':
            rate = self.size / im.size[1]
        else:
            rate = 1
        
        print '\tRate = ' + str(rate) + '\n'
        
        width, height = im.size
        width = int(width * rate)
        height = int(height * rate)
        
        print '\tNew size = ' + str((width, height)) + ' px\n'
        
        return im.resize((width, height))
    
    def resize_image_with_ratio(self, im):
        if self.dimension != 'r':
            return im # zadna zmena
        
        # u pomeru chci vzdy docilit vypoctu vetsi ku mensi strana
        requested_ratio = self.size[0] / self.size[1] if self.size[0] > self.size[1] else self.size[1] / self.size[0]
        im_ratio = float(im.size[0]) / im.size[1] if im.size[0] > im.size[1] else float(im.size[1]) / im.size[0]
        
        if requested_ratio == im_ratio:
            return im # zadna zmena
        
        print '\tOriginal ratio = ' + str(im_ratio) + '\n'
        print '\tRequested ratio = ' + str(requested_ratio) + '\n'
        
        # prevadeny obrazek muze byt navysku nebo na sirku, dle toho se musi upravit patricna strana
        extended_dimension = None
        if requested_ratio > im_ratio:
            extended_dimension = int(im.size[0] <= im.size[1]) # chci vetsi - napr. [0] < [1] => true => int(true) = [1]; jsou-li si rovny, nezalezi ktery beru
        else:
            extended_dimension = int(im.size[0] >= im.size[1]) # chci mensi - napr. [0] < [1] => false => int(false) = [0]; jsou-li si rovny, nezalezi ktery beru
        
        new_size = [im.size[0], im.size[1]]
        
        # rozsirovanou stranu vzdy zvetsim, aby pod se dala dat byla vypln
        new_size[extended_dimension] = int(new_size[int(not extended_dimension)] * requested_ratio)
            
        print '\tNew size = ' + str(new_size) + ' px\n'
        
        new_image = Image.new(im.mode, new_size, (255,255,255))
        
        position_of_pasted_img = [0, 0]
        # vkladany obrazek vycentruji na rozsirene strane
        position_of_pasted_img[extended_dimension] = (new_size[extended_dimension] - im.size[extended_dimension]) / 2
        
        new_image.paste(im, tuple(position_of_pasted_img))
        
        return new_image

if __name__ == '__main__':
    app = ImageResizer()
    app.main()
