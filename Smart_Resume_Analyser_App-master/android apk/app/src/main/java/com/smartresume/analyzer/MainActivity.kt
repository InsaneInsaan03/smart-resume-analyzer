package com.smartresume.analyzer

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.*
import android.view.View
import android.widget.ProgressBar
import androidx.activity.ComponentActivity
import android.os.Handler
import android.os.Looper
import android.widget.Toast

class MainActivity : ComponentActivity() {
    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private var isPageLoadTimeout = false
    private val PAGE_LOAD_TIMEOUT = 15000L // 15 seconds timeout

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        progressBar = findViewById(R.id.progressBar)

        setupWebView()
        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState)
        } else {
            loadInitialUrl()
        }
    }

    private fun setupWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            loadWithOverviewMode = true
            useWideViewPort = true
            builtInZoomControls = true
            displayZoomControls = false
            cacheMode = WebSettings.LOAD_NO_CACHE
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
        }

        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                isPageLoadTimeout = false
                progressBar.visibility = View.GONE
                webView.visibility = View.VISIBLE
            }

            override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                super.onReceivedError(view, request, error)
                // Handle errors like timeout, no internet etc.
                Toast.makeText(this@MainActivity, "Error loading page. Please try again.", Toast.LENGTH_SHORT).show()
                progressBar.visibility = View.GONE
            }

            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                request?.url?.let { url ->
                    if (url.scheme in listOf("http", "https")) {
                        return false // Let WebView handle standard URLs
                    }
                }
                return true // Block non-standard URLs
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                super.onProgressChanged(view, newProgress)
                progressBar.progress = newProgress
            }
        }
    }

    private fun loadInitialUrl() {
        progressBar.visibility = View.VISIBLE
        webView.visibility = View.INVISIBLE
        
        // Set timeout for page load
        Handler(Looper.getMainLooper()).postDelayed({
            if (progressBar.visibility == View.VISIBLE) {
                isPageLoadTimeout = true
                progressBar.visibility = View.GONE
                webView.stopLoading()
                Toast.makeText(this, "Page load timed out. Please check your connection.", Toast.LENGTH_LONG).show()
            }
        }, PAGE_LOAD_TIMEOUT)

        webView.loadUrl("YOUR_STREAMLIT_APP_URL") // Replace with your actual URL
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }

    override fun onBackPressed() {
        when {
            webView.canGoBack() && !isPageLoadTimeout -> {
                webView.goBack()
            }
            isPageLoadTimeout -> {
                // If page timed out, try reloading on back press
                isPageLoadTimeout = false
                loadInitialUrl()
            }
            else -> {
                super.onBackPressed()
            }
        }
    }

    override fun onDestroy() {
        webView.stopLoading()
        webView.onPause()
        webView.clearCache(true)
        super.onDestroy()
    }
}
