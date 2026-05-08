#!/usr/bin/env python3
"""
Shopping Scout - Price Extraction and Analysis
Reemplaza omnisearch + extract de OpenClaw
"""

import re
import json
import sys
import os
from datetime import datetime, timezone
from typing import Optional

def extract_prices(html: str, url: str) -> list[dict]:
    """Extrae precios en Soles (S/) y USD ($) de HTML."""
    if not html:
        return []

    prices = []
    try:
        domain = re.sub(r'^https?://(www\.)?', '', url.split('/')[2] if '://' in url else url)
        domain = domain.split('?')[0].split('#')[0]
    except:
        domain = url

    # Soles: S/ XXX
    s_matches = re.findall(r'S/\s*([\d.,]+)', html)
    for m in s_matches:
        try:
            price = float(m.replace(',', ''))
            if 0 < price < 1000000:
                prices.append({'price': price, 'currency': 'S/', 'domain': domain, 'url': url})
        except:
            pass

    # USD: $ XXX
    d_matches = re.findall(r'\$\s*([\d.,]+)', html)
    for m in d_matches:
        try:
            price = float(m.replace(',', ''))
            if 0 < price < 1000000:
                prices.append({'price': price, 'currency': 'USD', 'domain': domain, 'url': url})
        except:
            pass

    # Deduplicate by (domain, price, currency)
    seen = set()
    deduped = []
    for p in prices:
        key = (p['domain'], p['price'], p['currency'])
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    return deduped


def analyze_changes(prev: Optional[list], curr: list) -> dict:
    """Compara precios actuales con historial previo."""
    if not prev:
        return {
            'newProviders': sorted(set(r['domain'] for r in curr)),
            'removedProviders': [],
            'changes': []
        }

    prev_map = {(r['domain'], r['currency']): r['price'] for r in prev}
    curr_map = {(r['domain'], r['currency']): r['price'] for r in curr}

    prev_domains = set(prev_map.keys())
    curr_domains = set(curr_map.keys())

    new_providers = sorted(set(d for d, c in curr_domains if (d, c) not in prev_domains))
    removed = sorted(set(d for d, c in prev_domains if (d, c) not in curr_domains))

    changes = []
    for (domain, currency), price in curr_map:
        prev_price = prev_map.get((domain, currency))
        if prev_price and prev_price != price:
            diff = (price - prev_price) / prev_price * 100
            if abs(diff) > 0.5:
                changes.append({
                    'domain': domain,
                    'currency': currency,
                    'prev': prev_price,
                    'curr': price,
                    'diff': round(diff, 2)
                })

    changes.sort(key=lambda x: abs(x['diff']), reverse=True)
    return {
        'newProviders': new_providers,
        'removedProviders': removed,
        'changes': changes
    }


def load_history(history_file: str) -> Optional[list]:
    """Carga el último snapshot de precios del historial."""
    if not os.path.exists(history_file):
        return None
    try:
        with open(history_file) as f:
            data = json.load(f)
        history = data.get('history', {})
        if not history:
            return None
        timestamps = sorted(history.keys())
        if len(timestamps) < 2:
            return None
        return history[timestamps[-2]].get('prices')
    except:
        return None


def save_history(history_file: str, query: str, query_id: str, prices: list):
    """Guarda un nuevo snapshot de precios."""
    data = {
        'query': query,
        'id': query_id,
        'history': {}
    }
    if os.path.exists(history_file):
        try:
            with open(history_file) as f:
                data = json.load(f)
        except:
            pass

    timestamp = datetime.now(timezone.utc).isoformat()
    data['history'][timestamp] = {'prices': prices}
    data['query'] = query
    data['id'] = query_id

    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    with open(history_file, 'w') as f:
        json.dump(data, f, indent=2)


def load_config(config_file: str) -> dict:
    """Carga config.json de queries."""
    if not os.path.exists(config_file):
        return {'queries': []}
    try:
        with open(config_file) as f:
            return json.load(f)
    except:
        return {'queries': []}


def save_config(config_file: str, config: dict):
    """Guarda config.json de queries."""
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)


def format_report(query: str, prices: list, analysis: dict) -> str:
    """Genera reporte legible."""
    date = datetime.now().strftime('%Y-%m-%d')
    lines = [f"🛒 **{query}** ({date})\n"]

    if not prices:
        lines.append('_No se encontraron precios_')
        return '\n'.join(lines)

    new_p = analysis.get('newProviders', [])
    removed = analysis.get('removedProviders', [])
    changes = analysis.get('changes', [])

    if new_p:
        lines.append(f"🆕 **Nuevos:** {', '.join(new_p)}")
    if removed:
        lines.append(f"❌ **Desaparecidos:** {', '.join(removed)}")

    if changes:
        lines.append('\n**Cambios:**')
        for c in changes:
            emoji = '📈' if c['diff'] > 0 else '📉'
            lines.append(f"• {c['domain']}: {c['currency']}{c['curr']} ({emoji} {c['diff']:+.1f}%)")
        lines.append('')

    prices_sorted = sorted(prices, key=lambda x: (x['currency'], x['price']))
    lines.append('**Precios:**')
    for i, r in enumerate(prices_sorted, 1):
        chg = next((c for c in changes if c['domain'] == r['domain']), None)
        tag = ''
        if chg:
            tag = ' 📈' if chg['diff'] > 0 else ' 📉'
        lines.append(f"{i}. **{r['domain']}**: {r['currency']}{r['price']}{tag}")

    return '\n'.join(lines)


def make_query_id(query: str) -> str:
    """Genera ID sanitizado para el query."""
    import hashlib
    sanitized = re.sub(r'[^a-zA-Z0-9\s]', '', query.lower())
    sanitized = re.sub(r'\s+', '-', sanitized.strip())
    short = hashlib.md5(query.lower().encode()).hexdigest()[:6]
    return f"{sanitized}-{short}"


if __name__ == '__main__':
    # CLI simple para testing: python check_prices.py --html "..." --url "..."
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--html')
    parser.add_argument('--url', default='https://example.com')
    parser.add_argument('--query')
    parser.add_argument('--output-dir', default='output/prices')
    parser.add_argument('--config-file', default='output/config.json')
    args = parser.parse_args()

    if args.html and args.query:
        prices = extract_prices(args.html, args.url)
        qid = make_query_id(args.query)
        hist_file = os.path.join(args.output_dir, f"{qid}.json")
        prev = load_history(hist_file)
        analysis = analyze_changes(prev, prices)
        save_history(hist_file, args.query, qid, prices)
        print(format_report(args.query, prices, analysis))
    elif args.query:
        # Solo generar ID
        print(make_query_id(args.query))
    else:
        print("Usage: check_prices.py --html '<html>' --url '<url>' --query '<query>'")
        sys.exit(1)
