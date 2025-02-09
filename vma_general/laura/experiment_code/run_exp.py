from __future__ import division
from psychopy import visual, core, data, event, sound
from psychopy.constants import *
from psychopy import parallel
from psychopy.tools import coordinatetools
from psychopy.tools import mathtools
import datetime
import os
import sys
import serial
import time
import struct
import numpy as np
import pandas as pd

sub_num = 0

win = visual.Window(size=(700, 700),
                    pos=(100, 100),
                    fullscr=False,
                    screen=0,
                    allowGUI=False,
                    allowStencil=False,
                    monitor='testMonitor',
                    color='gray',
                    colorSpace='rgb',
                    blendMode='avg',
                    useFBO=False,
                    units='cm')

search_circle = visual.Circle(win,
                              radius=0.5,
                              lineColor='white',
                              fillColor=None)
start_circle = visual.Circle(win, radius=0.5, fillColor='blue')
target_circle = visual.Circle(win, radius=0.5, fillColor='blue')
feedback_circle = visual.Circle(win, radius=0.35, fillColor='white')
cursor_circle = visual.Circle(win, radius=0.35, fillColor='white')
cursor_cloud = [visual.Circle(win, radius=0.35, fillColor='white')] * 10

text_stim = visual.TextStim(win=win,
                            ori=0,
                            name='text',
                            text='',
                            font='Arial',
                            pos=(0, 8),
                            height=1,
                            wrapWidth=None,
                            color='white',
                            colorSpace='rgb',
                            opacity=1,
                            bold=False,
                            anchorHoriz='center',
                            anchorVert='center')

mouse = event.Mouse(visible=False, win=win)

target_distance = 6
target_circle.pos = (0, target_distance)

config = pd.read_csv('../config/config_reach_' + str(sub_num) + '.csv')

cursor_vis = config['cursor_vis']
midpoint_vis = config['midpoint_vis']
endpoint_vis = config['endpoint_vis']
cursor_sig = config['cursor_sig']
cursor_mp_sig = config['cursor_mp_sig']
cursor_ep_sig = config['cursor_ep_sig']
clamp = config['clamp']
rot = config['rot']
trial = config['trial']
cycle = config['cycle']
target_angle = config['target_angle']
instruct_phase = config['instruct_phase']
instruct_state = config['instruct_state']

num_trials = config.shape[0]

state = 'trial_init'

t_instruct = 1.0
t_hold = 1.0
t_move_prep = 0.0  # TODO if we choose to use this then we need some go cue
t_iti = 1.0
t_feedback = 1.0
t_mp = 0.3
t_too_fast = 0.1
t_too_slow = 0.8

search_near_thresh = 0.1
search_ring_thresh = 1.0

current_trial = 0
current_sample = 0

experiment_clock = core.Clock()
state_clock = core.Clock()
mp_clock = core.Clock()

while current_trial < num_trials:

    resp = event.getKeys(keyList=['escape'])
    rt = state_clock.getTime()

    x, y = mouse.getPos()
    theta, r = coordinatetools.cart2pol(x, y)

    cursor_circle.pos = (x, y)

    if state == 'trial_init':

        trial_data = {
            'cursor_vis': [],
            'midpoint_vis': [],
            'endpoint_vis': [],
            'cursor_sig': [],
            'cursor_mp_sig': [],
            'cursor_ep_sig': [],
            'clamp': [],
            'rot': [],
            'trial': [],
            'cycle': [],
            'target_angle': [],
            'instruct_phase': [],
            'instruct_state': [],
            'endpoint_theta': [],
            'movement_time': [],
            'movement_initiation_time': []
        }

        trial_move = {
            'trial': [],
            'state': [],
            'sample': [],
            'time': [],
            'x': [],
            'y': []
        }

        cursor_cloud_jitter_mp = np.random.multivariate_normal(
            [0, 0], [[cursor_mp_sig[current_trial], 0],
                     [0, cursor_mp_sig[current_trial]]], len(cursor_cloud))

        cursor_cloud_jitter_ep = np.random.multivariate_normal(
            [0, 0], [[cursor_ep_sig[current_trial], 0],
                     [0, cursor_ep_sig[current_trial]]], len(cursor_cloud))

        endpoint_theta = -1
        movement_time = -1
        movement_initiation_time = -1

        state = 'search_ring'

    if state == 'search_ring':
        if instruct_state[current_trial]:
            text_stim.text = 'Move your hand to make the diameter of the ring shrink'
            text_stim.draw()
        search_circle.radius = r
        search_circle.draw()
        if mathtools.distance(start_circle.pos,
                              cursor_circle.pos) < search_ring_thresh:
            state = 'search_near'
            state_clock.reset()

    if state == 'search_near':
        if instruct_state[current_trial]:
            text_stim.text = 'Move the cursor all the way inside the start circle'
            text_stim.draw()

        start_circle.draw()
        cursor_circle.draw()

        if mathtools.distance(start_circle.pos,
                              cursor_circle.pos) >= search_ring_thresh:
            state = 'search_ring'
            state_clock.reset()
        elif mathtools.distance(start_circle.pos,
                                cursor_circle.pos) < search_near_thresh:
            state = 'hold'
            state_clock.reset()

    if state == 'instruct':
        if instruct[current_trial] != 'NaN':
            text_stim.text = instruct[current_trial]
            text_stim.draw()

            if mathtools.distance(start_circle.pos,
                                  cursor_circle.pos) >= search_near_thresh:
                state = 'search_near'
                state_clock.reset()
            elif state_clock.getTime() >= t_instruct:
                state = 'hold'
                state_clock.reset()
        else:
            state = 'hold'
            state_clock.reset()

    if state == 'hold':
        if instruct_state[current_trial]:
            text_stim.text = 'Hold the cursor steady inside the start circle'
            text_stim.draw()

        start_circle.draw()
        cursor_circle.draw()
        if mathtools.distance(start_circle.pos, cursor_circle.pos) >= 0.1:
            state = 'search_near'
            state_clock.reset()
        elif state_clock.getTime() >= t_hold:
            state = 'move_prep'
            state_clock.reset()

    if state == 'move_prep':
        if instruct_state[current_trial]:
            text_stim.text = 'Slice through the target as quickly and accurately as possible'
            text_stim.draw()

        start_circle.draw()
        cursor_circle.draw()
        target_circle.pos = coordinatetools.pol2cart(
            target_angle[current_trial], target_distance)
        target_circle.draw()

        if state_clock.getTime() >= t_move_prep:
            if mathtools.distance(start_circle.pos,
                                  cursor_circle.pos) >= search_near_thresh:
                movement_initiation_time = state_clock.getTime()
                state = 'reach'
                state_clock.reset()
        else:
            if mathtools.distance(start_circle.pos,
                                  cursor_circle.pos) >= search_near_thresh:
                state = 'search_near'
                state_clock.reset()

    if state == 'reach':
        if instruct_state[current_trial]:
            text_stim.text = 'Reaching...'
            text_stim.draw()

        target_circle.draw()
        start_circle.draw()

        if clamp[current_trial] == True:
            cursor_circle.pos = coordinatetools.pol2cart(
                target_angle[current_trial] + rot[current_trial], r)
        else:
            cursor_circle.pos = coordinatetools.pol2cart(
                theta + rot[current_trial], r)

        if cursor_vis[current_trial]:
            cursor_circle.draw()

        if midpoint_vis[current_trial]:
            if r >= target_distance / 2:
                if mp_clock.getTime() < t_mp:
                    for i in range(len(cursor_cloud)):
                        cx = x + cursor_cloud_jitter_mp[i][0]
                        cy = y + cursor_cloud_jitter_mp[i][1]
                        cursor_cloud[i].pos = (cx, cy)
                        cursor_cloud[i].draw()
            else:
                mp_clock.reset()

        if mathtools.distance(start_circle.pos, (x, y)) >= target_distance:
            if clamp[current_trial] == True:
                feedback_circle.pos = coordinatetools.pol2cart(
                    target_angle[current_trial] + rot[current_trial],
                    target_distance)
            else:
                feedback_circle.pos = coordinatetools.pol2cart(
                    theta + rot[current_trial], target_distance)

            endpoint_theta = coordinatetools.cart2pol(mouse.getPos()[0],
                                                      mouse.getPos()[1])[0]
            movement_time = state_clock.getTime()
            state = 'feedback'
            state_clock.reset()

    if state == 'feedback':
        if movement_time > t_too_slow:
            text_stim.text = 'Please execute your movement more quickly'
            text_stim.draw()

        elif movement_time < t_too_fast:
            text_stim.text = 'Please execute your movement more slowly'
            text_stim.draw()

        else:

            start_circle.draw()
            target_circle.draw()

            if endpoint_vis[current_trial]:
                if instruct_state[current_trial]:
                    text_stim.text = 'The on screen cursor shows you how accurate your reach was'
                    text_stim.draw()

                feedback_circle.draw()
                for i in range(len(cursor_cloud)):
                    cx = feedback_circle.pos[0] + cursor_cloud_jitter_ep[i][0]
                    cy = feedback_circle.pos[1] + cursor_cloud_jitter_ep[i][1]
                    cursor_cloud[i].pos = (cx, cy)
                    cursor_cloud[i].draw()

            else:
                if instruct_state[current_trial]:
                    text_stim.text = 'This is a no-feedback trial '
                    text_stim.text += 'so you do not get to see how accurate your reach was.'

                text_stim.draw()

        if state_clock.getTime() > t_feedback:
            state = 'iti'
            state_clock.reset()

    if state == 'iti':
        if instruct_state[current_trial]:
            text_stim.text = 'Please remain still and wait for further instructions'
            text_stim.draw()

        if state_clock.getTime() > t_iti:
            state = 'trial_init'

            trial_data = {
                'cursor_vis': [cursor_vis[current_trial]],
                'midpoint_vis': [midpoint_vis[current_trial]],
                'endpoint_vis': [endpoint_vis[current_trial]],
                'cursor_sig': [cursor_sig[current_trial]],
                'cursor_mp_sig': [cursor_mp_sig[current_trial]],
                'cursor_ep_sig': [cursor_ep_sig[current_trial]],
                'clamp': [clamp[current_trial]],
                'rot': [rot[current_trial]],
                'trial': [trial[current_trial]],
                'cycle': [cycle[current_trial]],
                'target_angle': [target_angle[current_trial]],
                'instruct_phase': [instruct_phase[current_trial]],
                'instruct_state': [instruct_state[current_trial]],
                'endpoint_theta': [endpoint_theta],
                'movement_time': [movement_time],
                'movement_initiation_time': [movement_initiation_time]
            }

            f_trial = '../data/data_trials_' + str(sub_num) + '.csv'
            pd.DataFrame(trial_data).to_csv(f_trial,
                                            header=not os.path.isfile(f_trial),
                                            mode='a')

            f_move = '../data/data_movements_' + str(sub_num) + '.csv'
            pd.DataFrame(trial_move).to_csv(f_move,
                                            header=not os.path.isfile(f_move),
                                            mode='a')

            current_trial += 1
            state_clock.reset()

    # trajectories recorded every sample
    trial_move['trial'].append(current_trial)
    trial_move['state'].append(state)
    trial_move['sample'].append(current_sample)
    trial_move['time'].append(experiment_clock.getTime())
    trial_move['x'].append(x)
    trial_move['y'].append(y)
    current_sample += 1
    win.flip()

    if 'escape' in resp:
        win.close()
        core.quit()

win.close()
core.quit()
