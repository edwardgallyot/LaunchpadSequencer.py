import rtmidi
import time
import random

# Global Midi Parameters with RtMidi
# You can find your midi ports on your own computer using the .get_ports() method on a rtmidi object in a Python console

midi_out = rtmidi.MidiOut()
midi_out.open_port(0)
midi_in = rtmidi.MidiIn()
midi_in.open_port(0)
moog_send = rtmidi.MidiOut()
moog_send.open_port(3)


# Creating a class for the launchpad with a C major scale in MIDI
# There are empty dictionaries and lists for storing the Values received and to be sent to the launchpad

class Launchpad:
    scale = [72, 71, 69, 67, 65, 64, 62, 60]
    sends = []
    meter = 7
    notes_on = {}
    column_on = {}
    #Here are some global MIDI parameters for the Launchpad MK1 which made sense to have as class variables.
    make_blank = 0
    make_red = 15
    make_green = 60
    make_yellow = 63
    send_on = 0x90
    send_off = 0x80

    # The Launchpad Objects sends and recieves MIDI to the lights of the launchpad
    
    def __init__(self, message, note, velocity):
        if message == True:
            self.message = self.send_on
        if message == False:
            self.message = self.send_off
        self.note = note
        self.velocity = velocity

    def turn_on(self):
        return [self.send_on, self.note, self.velocity]

    def turn_off(self):
        self.velocity = self.make_blank
        return [self.send_off, self.note, self.velocity]

    def set_note(self, notechange):
        self.note = notechange

    def red(self):
        self.velocity = self.make_red

    def green(self):
        self.velocity = self.make_green

    def yellow(self):
        self.velocity = self.make_yellow

    @classmethod
    def from_midi_input_on(cls):
        message = midi_in.get_message()
        if message != None:
            note_pressed = message[0][1]
            trigger = message[0][2]
            if note_pressed not in cls.notes_on and trigger == 127:
                cls.notes_on.setdefault(note_pressed, 'On')
                light_on = Launchpad(cls.send_on, note_pressed, cls.make_yellow)
                midi_out.send_message(light_on.turn_on())
            elif note_pressed in cls.notes_on.keys() and trigger == 127:
                light_off = Launchpad(cls.send_off, note_pressed, cls.make_blank)
                midi_out.send_message(light_off.turn_off())
                del cls.notes_on[note_pressed]
        else:
            return None

    @classmethod
    def notes_on_now(cls):
        for key in cls.notes_on.keys():
            midi_out.send_message([cls.send_on, key, cls.make_yellow])


# I also created a subclass for triggering the columns of lights along the launchpad
# If a red light runs over a note value that is on it will make that note green

class Column_Lights(Launchpad):

    def __init__(self, message, note, velocity, beat):
        super().__init__(message, note, velocity)
        self.beat = beat

    def turn_on_column(self):
        for notes in range(8):
            note_on = beat + (16 * notes)
            self.column_on[notes] = note_on
            if note_on not in self.notes_on:
                midi_out.send_message([self.send_on, note_on, self.make_red])
            if note_on in self.notes_on:
                midi_out.send_message([self.send_on, note_on, self.make_green])

    def turn_off_column(self):
        for k, v in self.column_on.items():
            if v not in self.notes_on:
                midi_out.send_message([self.send_off, v, self.make_blank])
            if v in self.notes_on:
                midi_out.send_message([self.send_on, v, self.make_yellow])


# This Midi_Send sub-class looks at the dictionarys of notes on, columns on and at the beat in the main program loop
# If there is a match in all three of these parameters it sends a message to the MIDI send.

class Midi_Send(Column_Lights):
    def __init__(self, message, note, velocity, beat):
        super().__init__(message, note, velocity, beat)

    def send_midi_on(self):
        for k, v in self.column_on.items():
            if v in self.notes_on.keys() and self.beat == v % 16:
                moog_send.send_message([self.send_on, self.scale[k], self.velocity])
                self.sends.append(self.scale[k])

    def send_midi_off(self):
        for note in self.sends:
            if note in self.sends:
                moog_send.send_message([self.send_off, note, self.velocity])
                self.sends.remove(note)


# The main program loop
# The beat comes from a time slept iteration of the meter

while True:

    try:
        tempo = 122.8
        eigth_note = 30 / tempo
        Launchpad.meter = 8
        midi_out.send_message([176, 0, 0])
        Launchpad.notes_on_now()
        for beat in range(Launchpad.meter):
            Launchpad.from_midi_input_on()
            column = Column_Lights(True, None, Launchpad.make_yellow, beat)
            column.turn_on_column()
            moog = Midi_Send(True, None, random.randint(54, 100), beat)
            moog.send_midi_on()
            time.sleep(eigth_note)
            moog.send_midi_off()
            column.turn_off_column()

    except KeyboardInterrupt:
        midi_out.send_message([176, 0, 0])
        midi_in.close_port()
        moog_send.close_port()
        midi_out.close_port()
