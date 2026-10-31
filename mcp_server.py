#!/usr/bin/env python3
"""MCP stdio tools for the same saved configurations and runs as the GUI."""
import json
import sys
from job_service import JobService

NAME = 'chaos-security-benchmark'
VERSION = '1.0.0'
MODERN = '2026-07-28'
LEGACY = '2025-11-25'
SERVER_INFO = {'name': NAME, 'version': VERSION}


def schema(properties=None, required=None):
    return {'type': 'object', 'properties': properties or {},
            'required': required or [], 'additionalProperties': False}


TOOLS = [
    {'name': 'list_configs', 'description': 'List saved, validated benchmark configurations.',
     'inputSchema': schema()},
    {'name': 'get_config', 'description': 'Read a saved benchmark configuration.',
     'inputSchema': schema({'config_id': {'type': 'string'}}, ['config_id'])},
    {'name': 'start_run', 'description': 'Start matched plain and chaos runs for a saved configuration.',
     'inputSchema': schema({'config_id': {'type': 'string'}}, ['config_id'])},
    {'name': 'get_run', 'description': 'Read the status of a run. Poll until it finishes.',
     'inputSchema': schema({'run_id': {'type': 'string'}}, ['run_id'])},
    {'name': 'list_runs', 'description': 'List recent runs.', 'inputSchema': schema()},
    {'name': 'read_receipt', 'description': 'Read results and verified witnesses of a successful run.',
     'inputSchema': schema({'run_id': {'type': 'string'}}, ['run_id'])},
    {'name': 'cancel_run', 'description': 'Stop an active run.',
     'inputSchema': schema({'run_id': {'type': 'string'}}, ['run_id'])},
]


def result_response(identifier, result, modern):
    if modern:
        result = {'resultType': 'complete', **result,
                  '_meta': {'io.modelcontextprotocol/serverInfo': SERVER_INFO}}
    return {'jsonrpc': '2.0', 'id': identifier, 'result': result}


def error_response(identifier, code, message, data=None):
    error = {'code': code, 'message': message}
    if data is not None:
        error['data'] = data
    return {'jsonrpc': '2.0', 'id': identifier, 'error': error}


def tool_call(service, name, args):
    if not isinstance(args, dict):
        raise ValueError('arguments must be an object')
    if name in ('list_configs', 'list_runs') and args:
        raise ValueError('this tool accepts no arguments')
    if name == 'list_configs':
        return {'configs': service.list_configs()}
    if name == 'list_runs':
        return {'runs': service.list_runs()}
    if name == 'get_config':
        return service.get_config(args['config_id'])
    if name == 'start_run':
        return service.start_run(args['config_id'])
    if name == 'get_run':
        return service.get_run(args['run_id'])
    if name == 'read_receipt':
        return service.receipt(args['run_id'])
    if name == 'cancel_run':
        return service.cancel_run(args['run_id'])
    raise ValueError('unknown tool')


def dispatch(service, message, initialized):
    if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
        return error_response(message.get('id') if isinstance(message, dict) else None,
                              -32600, 'Invalid Request'), initialized
    if 'id' not in message:
        return None, initialized
    identifier = message['id']
    method = message.get('method')
    params = message.get('params') or {}
    if not isinstance(params, dict):
        return error_response(identifier, -32602, 'Invalid params'), initialized
    if method == 'initialize':
        requested = params.get('protocolVersion')
        version = requested if requested in (LEGACY, '2025-06-18', '2025-03-26') else LEGACY
        return result_response(identifier, {'protocolVersion': version,
            'capabilities': {'tools': {'listChanged': False}}, 'serverInfo': SERVER_INFO}, False), True
    version = params.get('_meta', {}).get('io.modelcontextprotocol/protocolVersion') if isinstance(params.get('_meta', {}), dict) else None
    modern = version == MODERN
    if method == 'server/discover':
        if not modern:
            return error_response(identifier, -32022, 'Unsupported protocol version',
                                  {'supported': [MODERN, LEGACY], 'requested': version}), initialized
        return result_response(identifier, {'supportedVersions': [MODERN, LEGACY],
            'capabilities': {'tools': {'listChanged': False}}, 'ttlMs': 0,
            'cacheScope': 'private'}, True), initialized
    if version is not None and not modern:
        return error_response(identifier, -32022, 'Unsupported protocol version',
                              {'supported': [MODERN, LEGACY], 'requested': version}), initialized
    if not modern and not initialized:
        return error_response(identifier, -32000, 'Initialize first'), initialized
    if method == 'ping':
        return result_response(identifier, {}, modern), initialized
    if method == 'tools/list':
        response = {'tools': TOOLS}
        if modern:
            response.update(ttlMs=0, cacheScope='private')
        return result_response(identifier, response, modern), initialized
    if method == 'tools/call':
        name, args = params.get('name'), params.get('arguments', {})
        if not isinstance(name, str):
            return error_response(identifier, -32602, 'Tool name required'), initialized
        try:
            data = tool_call(service, name, args)
            response = {'content': [{'type': 'text', 'text': json.dumps(data, ensure_ascii=False)}],
                        'structuredContent': data, 'isError': False}
        except (ValueError, OSError, KeyError) as error:
            response = {'content': [{'type': 'text', 'text': str(error)}], 'isError': True}
        return result_response(identifier, response, modern), initialized
    return error_response(identifier, -32601, 'Method not found'), initialized


def main():
    service = JobService()
    initialized = False
    try:
        while raw := sys.stdin.buffer.readline(4 * 1024 * 1024 + 1):
            if len(raw) > 4 * 1024 * 1024:
                response = error_response(None, -32700, 'Message too large')
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()
                break
            else:
                try:
                    message = json.loads(raw)
                    response, initialized = dispatch(service, message, initialized)
                except (ValueError, UnicodeDecodeError):
                    response = error_response(None, -32700, 'Parse error')
            if response is not None:
                sys.stdout.write(json.dumps(response, separators=(',', ':'), ensure_ascii=False) + '\n')
                sys.stdout.flush()
    finally:
        service.shutdown()


if __name__ == '__main__':
    main()
