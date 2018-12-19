from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app
from flask_login import current_user, login_required
from app import db, crawlerThread
from app.models import User, Products
from app.main import bp
from app.main.forms import SearchForm, CrawlForm
from app.browser.browser import getCrawlerThread

@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        g.search_form = SearchForm()

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    product_count = Products.query.count()
    products = Products.query.order_by(Products.id.asc()).paginate(
        page, current_app.config['PRODUCTS_PER_PAGE'], False)
    next_url = url_for('main.index', page=products.next_num) \
        if products.has_next else None
    prev_url = url_for('main.index', page=products.prev_num) \
        if products.has_prev else None
    return render_template('index.html', title='Home', products=products.items,
        next_url=next_url, prev_url=prev_url, product_count=product_count)


@bp.route('/crawler', methods=['GET', 'POST'])
@login_required
def crawler():
    global crawlerThread
    if crawlerThread and crawlerThread.is_alive():
        return render_template('crawler.html', running=True)
    form = CrawlForm()
    if form.validate_on_submit():
        crawlerThread = getCrawlerThread(current_app._get_current_object(), db)
        crawlerThread.start()
        flash('Start crawler successfully!')
        return render_template('crawler.html', running=True)
    return render_template('crawler.html', form=form, running=False)


@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if not g.search_form.validate():
        return render_template('index.html', title='Home')
    page = request.args.get('page', 1, type=int)
    products, total = Products.search(g.search_form.q.data, page,
        current_app.config['PRODUCTS_PER_PAGE'])

    start = current_app.config['PRODUCTS_PER_PAGE'] * (page-1)  
    if total > current_app.config['PRODUCTS_PER_PAGE'] * page:
        end = current_app.config['PRODUCTS_PER_PAGE'] * page + 1
    else:
        end = total
    if start < total:
        products = products[start:end]

    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['PRODUCTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None

    return render_template('index.html', title='Search', products=products,
                           total=total, next_url=next_url, prev_url=prev_url,
                           start=start, end=end, query=g.search_form.q.data)
