#!/usr/bin/env python3
# TODO: Add error handling

import sys
import os
import urllib.parse
import requests
from dotenv import load_dotenv

load_dotenv()

class Report:
    def __init__(self, report, api_key):
        self.report = report
        self.api_key = api_key

    def get_fights(self):
        url = f'https://www.warcraftlogs.com/v1/report/fights/{self.report}?api_key={self.api_key}'
        response = requests.get(url).json()
        fights = {}
        for fight in response['fights']:
            fights[fight['id']] = fight
        return fights

    def get_events(self, url, args, start_time, end_time):
        args['start'] = start_time
        args['end'] = end_time
        full_url = f'{url}?{urllib.parse.urlencode(args)}'
        response = requests.get(full_url).json()
        if 'nextPageTimestamp' in response:
            return [
                *response['events'],
                *self.get_events(url, args, response['nextPageTimestamp'], end_time)
            ]
        return response['events']

    def get_cast_events(self, start_time=0, end_time=999999999, **extraArgs):
        url = f'https://www.warcraftlogs.com/v1/report/events/casts/{self.report}'
        args = {
            'api_key': self.api_key,
            'hostility': 1,
            'translate': True,
            **extraArgs,
        }
        return self.get_events(url, args, start_time, end_time)

    @classmethod
    def get_timers(cls, events, start_time=0):
        timestamps = {}
        spell_names = {}
        for event in events:
            spell_id = event['ability']['guid']
            event_type = event['type']
            spell_names[spell_id] = event['ability']['name']
            if not event_type in timestamps:
                timestamps[event_type] = {}
            if not spell_id in timestamps[event_type]:
                timestamps[event_type][spell_id] = []

            timestamps[event_type][spell_id].append(event['timestamp'])
        timers = {}
        for event_type, spell_ids in timestamps.items():
            timers[event_type] = {}
            for spell_id, event_timestamps in spell_ids.items():
                timers[event_type][spell_id] = [
                    event_timestamps[i] - (event_timestamps[i - 1] if i >= 1 else start_time)
                    for i in range(0, len(event_timestamps))
                ]
        return (timers, spell_names)

def main():
    report = Report(sys.argv[1], os.getenv('wcl_api_key'))
    fights = report.get_fights()
    fight_id = int(sys.argv[2])
    if fight_id in fights:
        fight = fights[fight_id]
        events = report.get_cast_events(fight['start_time'], fight['end_time'])
        timers, spell_names = report.get_timers(events, fight['start_time'])
        for event_type, spells in timers.items():
            print(f'\n---{event_type}---')
            for spell_id, times in spells.items():
                times = [str(round(t/1000, 1)) for t in times]
                print(f'{spell_names[spell_id]}-{spell_id} = pull:{", ".join(times)}')

main()
