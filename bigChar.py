#!/usr/bin/python

# Display a big character (Upper case and lower case) in the middle of
# the screen when a letter is typed.  Plays a corresponding song for
# that letter.  This program can be used as a starting point to
# develop music playing capability with GStreamer 1.0 and beyond, or
# to learn Gtk programming with Python.

# It can also be used to teach children how to recognize the alphabet.
# This program is easy to use, it gives children a 26-key jukebox, and
# is not attractive enough to get them to spend countless hours in
# front of it.

# I hope you find this program instructive and useful.


# bigChar  Copyright (C) 2016 Vikram Aggarwal
# This program comes with ABSOLUTELY NO WARRANTY
# This is free software, and you are welcome to redistribute it
# under certain conditions.


import datetime, string, os

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, Gtk, Pango, Gdk, GObject


class AudioPlayer():
    """ A class that plays OGG Vorbis files. """
    def __init__(self):
        """ Initialize the Audio Player and set up Gstreamer """
        self.started = False
        # Change this location to indicate where the songs are stored.
        self.music_path = os.path.dirname(os.path.realpath(__file__)) + "/music/"
        print self.music_path

        Gst.init(None)
        # Create a pipeline
        self.pipeline = Gst.Pipeline.new("pipe")

        self.source = Gst.ElementFactory.make('filesrc')
        demux = Gst.ElementFactory.make('oggdemux')
        # The demux does not expose any pads till it has a file. Attach
        # a callback when pads are added
        demux.connect("pad-added", self.demuxer_callback)
        self.decoder = Gst.ElementFactory.make('vorbisdec')
        converter = Gst.ElementFactory.make('audioconvert')
        sink = Gst.ElementFactory.make('autoaudiosink')

        # Attach all the elements to the pipeline
        self.pipeline.add(self.source)
        self.pipeline.add(demux)
        self.pipeline.add(self.decoder)
        self.pipeline.add(converter)
        self.pipeline.add(sink)

        # Attach source -> demux & decoder  -> converter -> sink
        # demux -> decoder is done in the demuxer_callback
        self.source.link(demux)
        self.decoder.link(converter)
        converter.link(sink)

        # Attach a signal handler for being turned on
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

    def start(self, alphabet):
        """Starts playing music for the alphabet indicated.

        The alphabet is currently upper case, so your music files have
        to be X.ogg, Y.ogg, etc.
        """
        if (self.started):
            self.pipeline.set_state(Gst.State.NULL)

        # Specify <current_dir>/music/S.ogg as the file to play when
        # the letter 's' or 'S' is pressed.
        filename = self.music_path + ("%s.ogg" % alphabet)

        # Set this as the source filename
        self.source.set_property("location", filename)

        # Start playing the pipeline
        self.pipeline.set_state(Gst.State.PLAYING)
        self.started = True

    def on_message(self, bus, message):
        """ Graciously handle End Of Stream and Error cases."""
        t = message.type
        if t == Gst.MessageType.EOS:
            self.pipeline.set_state(Gst.State.NULL)
            self.started = False
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.pipeline.set_state(Gst.State.NULL)
            self.started = False

    def demuxer_callback(self, demuxer, pad):
        "Connects the demux to the vorbis decoder"
        # Get the decoder pad that will accept the demultiplexed output
        decoder_pad = self.decoder.get_static_pad("sink")
        # And connect the newly formed pad to it, thereby joining the
        # demultiplexer to the decoder.
        pad.link(decoder_pad)

    def stop(self):
        if (self.started):
            self.pipeline.set_state(Gst.State.NULL)
        self.started = False



class BigChar():
    """ Create a Gtk window for a single giant textview that accepts
        all keyboard input. """
    def on_key_press(self, widget, data=None):
        """ Intercept all keypress events and show ascii
            characters. This requires the CAPS_LOCK to be off.  We
            don't intercept CAPS NUM or SCROLL lock, probably
            should."""
        # Set the time, even if the keypress is irrelevant
        self.set_time()

        ascii_value = data.keyval
        # Print the keycode received
        # print ascii_value

        self.audio_player.stop()

        # Uppercase and lowercase letters
        if (ascii_value >= 97 and ascii_value <= 122):
            self.display_alphabet(ascii_value - 97)
        if (ascii_value >= 65 and ascii_value <= 90):
            self.display_alphabet(ascii_value - 65)
        # Numbers
        if (ascii_value >= 48 and ascii_value <= 57):
            self.display_number(ascii_value - 48)
        # Number pad
        if (ascii_value >= 65456 and ascii_value <= 65466):
            self.display_number(ascii_value - 65456)
        # Special characters on the number pad.
        if (ascii_value == 65450):
            self.display("*")
        if (ascii_value == 65451):
            self.display("+")
        if (ascii_value == 65454):
            self.display(".")
        if (ascii_value == 65453):
            self.display("-")
        # Backspace should produce a left-pointing arrow.
        if (ascii_value == 65288):
            self.display(u"\u2190")
        if (ascii_value == 65515):
            self.display(u"\u25a1")

    def display(self, text):
        """ Show the text in the textbox."""
        self.textBuffer.set_text(text)
        start = self.textBuffer.get_start_iter()
        end = self.textBuffer.get_end_iter()
        self.textBuffer.apply_tag_by_name("real_big", start, end)

    def display_alphabet(self, index):
        """ Show the English alphabet (CAPS and lower) at 0 indexed
            position 'A a' = 0, 'B b' = 1, ...
            Also plays the song corresponding to the alphabet. """
        big = string.ascii_uppercase[index]
        small = string.ascii_lowercase[index]
        self.audio_player.start(big)
        self.display(big + " " + small)

    def display_number(self, number):
        """ Show the Number and play the song corresponding to it"""
        self.audio_player.start(number)
        self.display("%d" % number)

    def realize_handler(self, widget):
        pixmap = GdkPixbuf.Pixbuf(None, 1, 1, 1)
        color = Gdk.Color(0, 0, 0)
        cursor = Gdk.Cursor(pixmap, color, 0, 0)
        widget.window.set_cursor(cursor)

    def set_time(self):
        """Set the progress indicator to the current time.  Shows time
           in a horizontal access with the morning being near the left
           edge and night being near the right edge."""
        current_time = datetime.datetime.now()
        # Total hours past since (assume children wake up at 6am)
        minutes_past = ((current_time.hour - 6)
                        * 60.0 + current_time.minute)
        if (minutes_past < self.day_end):
            fraction = minutes_past / self.day_end
        else:
            fraction = 1.0
        self.progress.set_fraction(fraction)

    def __init__(self):
        """ Create a window with a single giant text view. Disables
            all chrome. """
        # Foreground and background color are read from here.
        #background_color = "black"
        #foreground_color = "#1111ff"
        background_color = "green"
        foreground_color = "black"

        self.audio_player = AudioPlayer()

        self.w = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        # No border
        self.w.set_border_width(0)
        # Take over the entire screen
        self.w.fullscreen()

        # Connect the callback on_key_press to the signal key_press.
        self.w.connect("key_press_event", self.on_key_press)
        # self.w.connect("realize", self.realize_handler)
        # Make the widget aware of the signal to catch.
        self.w.set_events(Gdk.EventMask.KEY_PRESS_MASK)

        # Add a text view to show the key pressed
        textView = Gtk.TextView()
        # Disable a cursor in the text view.
        textView.set_editable(False)
        textView.set_can_focus(False)
        # Show the single character in the middle
        textView.set_justification(Gtk.Justification.CENTER)
        # This is the place we will write the character to
        self.textBuffer = textView.get_buffer()
        # Make the text view huge and bold
        fontdesc = Pango.FontDescription("monospace bold 400")
        textView.modify_font(fontdesc)

        # Creates a tag that is applied to the text every time
        tag = self.textBuffer.create_tag(
            "real_big"
            , background=background_color
            , foreground=foreground_color)
        # The progress bar shows the current proportion of awake-time
        # for a child.
        # Minutes are capped at 8am, which is when kids go to
        # bed. Expressed as minutes after 6am.
        self.day_end = ((20 - 6) * 60.0)
        self.progress = Gtk.ProgressBar()
        self.set_time()

        # Make the text view take the entire window
        vbox = Gtk.VBox(homogeneous=True, spacing=0)
        color = Gdk.Color.parse(background_color)[1]

        self.w.modify_bg(Gtk.StateType.NORMAL, color)
        self.progress.modify_bg(Gtk.StateType.NORMAL, color)
        textView.modify_bg(Gtk.StateType.NORMAL, color)

        vbox.pack_start(textView, fill=True, expand=False, padding=0)
        vbox.pack_start(self.progress, fill=False, expand=False, padding=0)

        self.w.add(vbox)

    def show(self):
        """ Show the window"""
        self.w.show_all()


if __name__ == '__main__':
    # Create a bigchar window, and show it.
    bigchar = BigChar()
    bigchar.show()
    GObject.threads_init()
    Gtk.main()
