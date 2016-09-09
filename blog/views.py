#coding:utf-8

from django.shortcuts import render_to_response, render, get_object_or_404, HttpResponseRedirect
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView
from django.contrib import auth
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.utils import timezone

import qrcode
from cStringIO import StringIO
import markdown,markdown2

from blog.models import Article, Category, Tag
from .models import BlogComment, UserProfile
from .forms import BlogCommentForm, UserForm, RegistForm, RetrieveForm



# Create your views here.
class IndexView(ListView):
    template_name = "blog/index.html"
    context_object_name = "article_list"

    def get_queryset(self):
        # 置顶的要在前面,要排列多个顺序是，以此添加进去即可
        article_list = Article.objects.filter(created_time__lte=timezone.now()).filter(status='p').order_by('-topped', '-created_time', '-last_modified_time')
        for article in article_list:
            if not article.abstract:
                if len(article.body) < 54:
                    article.abstract = article.body
                else:
                    article.abstract = article.body[:54]
        return article_list

    def get_context_data(self, **kwargs):
        kwargs['category_list'] = Category.objects.all().order_by('name')
        kwargs['date_archive'] = Article.objects.archive()
        kwargs['tag_list'] = Tag.objects.all().order_by('name')
        return super(IndexView, self).get_context_data(**kwargs)


class ArticleDetailView(DetailView):
    model = Article
    template_name = "blog/detail.html"
    context_object_name = "article"
    pk_url_kwarg = 'article_id'

    def get_object(self, queryset=None):
        obj = super(ArticleDetailView, self).get_object()
        obj.body = markdown2.markdown(obj.body,['codehilite'], extras=['fenced-code-blocks'])
        return obj

    
    def get_context_data(self, **kwargs):
        kwargs['comment_list'] = self.object.blogcomment_set.all()
        kwargs['form'] = BlogCommentForm()
        return super(ArticleDetailView, self).get_context_data(**kwargs)


class CategoryView(ListView):
    template_name = "blog/index.html"
    context_object_name = "article_list"

    def get_queryset(self):
        article_list = Article.objects.filter(category=self.kwargs['cate_id'], status='p')
        # for article in article_list:
            # article.body = markdown2.markdown(article.body, extras=['fenced-code-blocks'], )
        return article_list

    def get_context_data(self, **kwargs):
        kwargs['category_list'] = Category.objects.all().order_by('name')
        return super(CategoryView, self).get_context_data(**kwargs)


class TagView(ListView):
    template_name = "blog/index.html"
    context_object_name = "article_list"

    def get_queryset(self):
        article_list = Article.objects.filter(tags=self.kwargs['tag_id'], status='p')
        # for article in article_list:
            # article.body = markdown2.markdown(article.body, extras=['fenced-code-blocks'], )
        return article_list

    def get_context_data(self, **kwargs):
        kwargs['category_list'] = Category.objects.all().order_by('name')
        kwargs['tag_list'] = Tag.objects.all().order_by('name')
        return super(TagView, self).get_context_data(**kwargs)


class ArchiveView(ListView):
    template_name = "blog/index.html"
    context_object_name = "article_list"

    def get_queryset(self):
        year = int(self.kwargs['year'])
        month = int(self.kwargs['month'])
        article_list = Article.objects.filter(status='p', created_time__year=year, created_time__month=month)
        # for article in article_list:
            # article.body = markdown2.markdown(article.body, extras=['fenced-code-blocks'], )
        return article_list

    def get_context_data(self, **kwargs):
        kwargs['category_list'] = Category.objects.all().order_by('name')
        kwargs['tag_list'] = Tag.objects.all().order_by('name')
        kwargs['date_archive'] = Article.objects.archive()
        return super(ArchiveView, self).get_context_data(**kwargs)


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)
    
class CommentPostView(LoginRequiredMixin, FormView):
    form_class = BlogCommentForm
    template_name = 'blog/detail.html'


    def form_valid(self, form):
        target_article = get_object_or_404(Article, pk=self.kwargs['article_id'])
        comment = form.save(commit=False)
        comment.article = target_article
        comment.save()
        self.success_url = reverse('blog:detail', args=(target_article.id,))
        return HttpResponseRedirect(self.success_url)

    def form_invalid(self, form):
        target_article = get_object_or_404(Article, pk=self.kwargs['article_id'])
        return render(self.request, 'blog/detail.html', {
            'form': form,
            'article': target_article,
            'comment_list': target_article.blogcomment_set.all(),
        })

class LoginView(FormView):
    form_class = UserForm
    template_name = 'blog/login.html'
    
    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = auth.authenticate(username=username, password=password)
        # print user
        if user is not None and user.is_active:
            auth.login(self.request, user)
            self.request.session['username'] = username
            return HttpResponseRedirect('/')
            return render_to_response('blog/index.html', RequestContext(self.request, {'username':username}))
        else:
            login_info = "Username or password is error"
            return render(self.request, 'blog/login.html', {'form': form,'login_info':login_info})
            return render_to_response('blog/login.html', RequestContext(self.request, {'form': form,'login_info':login_info}))
    
    def form_invalid(self, form):
        login_info = 'input error'
        return render_to_response('blog/login.html', RequestContext(self.request, {'form': form, 'login_info':login_info}))
        
def login(request):
    login_info = ''
    if request.method == 'GET':
        form = UserForm()
        return render_to_response('blog/login.html', RequestContext(request, {'form':form}))
    else:
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = auth.authenticate(username=username, password=password)
            # print user
            if user is not None and user.is_active:
                auth.login(request, user)
                return render_to_response('blog/index.html', RequestContext(request, {'username':username}))
            else:
                login_info = "Username or password is error"
                return render_to_response('blog/login.html', RequestContext(request, {'form': form,'login_info':login_info}))
        else:
            login_info = 'input error'
            return render_to_response('blog/login.html', RequestContext(request, {'form': form, 'login_info':login_info}))
            
def regist(request):
    regist_info = ''
    if request.method == 'GET':
        form = RegistForm()
        # context, content, contents are the same(变量名不影响使用)
        contents = {'form':form}
        
        # those are the same
        return render(request, 'blog/regist.html', contents)
        return render(request, 'blog/regist.html', {'form':form})
        return render_to_response('blog/regist.html', RequestContext(request, {'form':form}))
    else:
        form = RegistForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password1 = form.cleaned_data['password1']
            password2 = form.cleaned_data['password2']
            phone     = form.cleaned_data['phone']
            if password1 == password2:
                user_filter_result = User.objects.filter(username=username) 
                if len(user_filter_result)>0:  
                    regist_info = "用户名已存在"
                    return render_to_response("blog/regist.html", RequestContext(request,{'form':form, 'regist_info':regist_info}))  
                else:
                    user = User.objects.create_user(username= username,password=password1)
                    #user.is_active=True  
                    user.save
                    user_profile = UserProfile()
                    user_profile.user_id = user.id
                    user_profile.phone = phone
                    user_profile.save()
                    regist_info = '注册成功'
                    return render_to_response('blog/regist.html', RequestContext(request, {'form': form,'regist_info':regist_info}))
            else:
                regist_info = "两次输入的密码不一致!" 
                return render_to_response("blog/regist.html", RequestContext(request,{'form':form, 'regist_info':regist_info}))  
        else:
            regist_info = 'input error'
            return render_to_response('blog/regist.html', RequestContext(request, {'form': form, 'regist_info':regist_info}))
        
@login_required
def logout(request):
    auth.logout(request)
    return HttpResponseRedirect("/")            
 
def retrieve(request):
    retrieve_info = ''
    user_not_exist = False
    if request.method == 'GET':
        form = RetrieveForm()
        return render_to_response('blog/retrieve.html', RequestContext(request, {'form':form}))
    else:
        form = RetrieveForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            phone     = form.cleaned_data['phone']
            password1 = form.cleaned_data['password1']
            password2 = form.cleaned_data['password2']
            try:
                user = get_object_or_404(User, username=username)
            except:
                user_not_exist = True
            if  user_not_exist or not user.is_active:  
                retrieve_info = "用户名不存在"
                # 这里在template中可以直接调用form或者retrieve_info
                return render_to_response("blog/retrieve.html", RequestContext(request,{'form':form, 'retrieve_info':retrieve_info}))  
            else:
                user_profile = get_object_or_404(UserProfile, user_id=user.id)
                phone_db = user_profile.phone
                if phone_db == phone:
                    if password1 == password2:
                        user.set_password(password1)
                        user.save()
                        retrieve_info = '密码修改成功'
                    else:
                        retrieve_info = "两次输入的密码不一致!" 
                else:
                    retrieve_info = "手机号有误"
                return render_to_response('blog/retrieve.html', RequestContext(request, {'form': form,'retrieve_info':retrieve_info}))
                    
        else:
            retrieve_info = 'input error'
            return render_to_response('blog/retrieve.html', RequestContext(request, {'form': form, 'retrieve_info':retrieve_info}))
    
            
def generate_qrcode(request):
    # print 'url_data:' + url_data
    # print request.get_full_path()
    # print request.path
    # print request.get_host()
    if request.method == 'POST':
        url_data = request.POST['target_url']
        # url_data = request.POST.get('name')
        if url_data == "if leave empty, it will be current url":
            img = qrcode.make(request.get_host()+request.path)
        else:
            img = qrcode.make(url_data)
        buf = StringIO()
        img.save(buf)
        image_stream = buf.getvalue()

        response = HttpResponse(image_stream, content_type='image/png')
        return response
    else:
        return HttpResponseRedirect('/')            
#class Login(FormView):
#    template_name = 'blog/login.html'
     
class Regist(FormView):
    template_name = 'blog/regist.html'
