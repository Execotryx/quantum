// Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
// Credits: Opus and Astra.
// Streaming C2.7 physical-error classifier. This is not a quantum verifier.
#include <algorithm>
#include <array>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

using U64 = std::uint64_t;
using Word = std::uint16_t;
constexpr int FINITE_N=1, FINITE_D=2, DROP=4, WINDOW17=8, WINDOW14=16, GCD=32;
static volatile std::sig_atomic_t stopping=0;
static void stop_handler(int) { stopping=1; }
static void require(bool ok,const char* message) { if(!ok)throw std::runtime_error(message); }

struct Field {
    std::array<int,4096> log{};
    std::array<Word,8190> exp{};
    std::array<Word,4096> inverse{},root{},square{};
    static Word manual(int a,int b) {
        int result=0;
        for(;b;b>>=1) {if(b&1)result^=a;a<<=1;if(a&4096)a^=0x1053;}
        return Word(result);
    }
    Field() {
        log.fill(-1);Word x=1;
        for(int i=0;i<4095;++i){require(log[x]<0,"primitive cycle");exp[i]=x;log[x]=i;x=manual(x,2);}
        require(x==1,"primitive return");
        for(int i=4095;i<8190;++i)exp[i]=exp[i-4095];
        for(int a=1;a<4096;++a){inverse[a]=exp[4095-log[a]];root[a]=exp[(2048*log[a])%4095];}
        for(int a=0;a<4096;++a)square[a]=mul(a,a);
    }
    Word mul(int a,int b) const {return a&&b?exp[log[a]+log[b]]:0;}
    Word div(int a,int b) const {require(b!=0,"zero field divisor");return mul(a,inverse[b]);}
    int trace(int a) const {int result=0;for(int i=0;i<12;++i){result^=a;a=square[a];}return result;}
};

struct Poly {
    std::array<Word,36> a{};
    int size=0;
    void trim(){while(size&&a[size-1]==0)--size;}
};
static Poly polynomial_product(const Field& f,const Poly& a,const Poly& b) {
    Poly out;if(!a.size||!b.size)return out;
    out.size=a.size+b.size-1;require(out.size<=36,"polynomial capacity");
    for(int i=0;i<a.size;++i)for(int j=0;j<b.size;++j)out.a[i+j]^=f.mul(a.a[i],b.a[j]);
    out.trim();return out;
}
struct ErrorWord {
    int weight=0;
    std::array<Word,35> roots{},values{};
};
struct HalfProfile {
    std::array<int,18> degrees{};
    int count=0,reason=0;
    std::uint32_t mask=0,drop2=0;
};
struct Result {
    int weight=0,reason=0,finite_slot=-1,finite_kind=0;
    std::array<Word,2> nrem{},drem{};
    HalfProfile half;
    Poly full;
};

struct Classifier {
    Field f;
    std::array<Word,35> kappas{};
    std::array<std::array<Word,4096>,35> constant_mul{};
    std::array<Word,4096> aU{};
    std::array<Poly,36> padding{};
    Classifier() {
        for(int i=0;i<35;++i){
            const int t=2*i;kappas[i]=2048^f.square[t]^t;
            require(f.trace(kappas[i])==1,"quadratic irreducibility");
            for(int k=0;k<i;++k)require(kappas[k]!=kappas[i],"quadratic distinctness");
            for(int x=0;x<4096;++x)constant_mul[i][x]=f.mul(kappas[i],x);
        }
        for(int a=1;a<4096;++a){
            Word v=a;const int base=f.square[a]^a;
            for(int i=0;i<35;++i)v=f.mul(v,base^kappas[i]);
            require(v!=0,"physical input multiplier unit");aU[a]=v;
        }
        for(int j=0;j<=35;++j){
            Poly p;p.size=(j%2==0?2:1);p.a[p.size-1]=1;
            for(int i=j;i<=33-(j%2==0);i+=2){Poly q;q.size=3;q.a[0]=kappas[i];q.a[1]=q.a[2]=1;p=polynomial_product(f,p,q);}
            require(p.size==36-j,"padding degree");padding[j]=p;
        }
    }
    std::array<Word,2> remainder(const Poly& p,int index) const {
        Word a=0,b=0;
        for(int i=p.size-1;i>=0;--i){const Word next=p.a[i]^constant_mul[index][b];b^=a;a=next;}
        return {a,b};
    }
    std::array<Word,2> qmul(std::array<Word,2> x,std::array<Word,2> y,int index) const {
        const Word z=f.mul(x[1],y[1]);
        return {Word(f.mul(x[0],y[0])^constant_mul[index][z]),
                Word(f.mul(x[0],y[1])^f.mul(x[1],y[0])^z)};
    }
    std::array<Word,2> qdiv(std::array<Word,2> x,std::array<Word,2> y,int index) const {
        const Word norm=f.square[y[0]]^f.mul(y[0],y[1])^constant_mul[index][f.square[y[1]]];
        require(norm!=0,"quadratic denominator");
        return qmul(x,{f.mul(y[0]^y[1],f.inverse[norm]),f.mul(y[1],f.inverse[norm])},index);
    }
    void physical_pair(const ErrorWord& e,Poly& n,Poly& d) const {
        require(e.weight>=0&&e.weight<=35,"physical weight");
        d.size=1;d.a[0]=1;n.size=e.weight;
        for(int k=0;k<e.weight;++k){
            const Word root=e.roots[k];
            require(root>0&&root<4096&&e.values[k]>0&&e.values[k]<4096,"physical word range");
            for(int z=0;z<k;++z)require(e.roots[z]!=root,"duplicate physical root");
            d.a[d.size]=d.a[d.size-1];
            for(int i=d.size-1;i>0;--i)d.a[i]=d.a[i-1]^f.mul(root,d.a[i]);
            d.a[0]=f.mul(root,d.a[0]);++d.size;
        }
        for(int k=0;k<e.weight;++k){
            const Word root=e.roots[k],amplitude=f.mul(e.values[k],aU[root]);
            Word value=d.a[e.weight];
            for(int i=e.weight-1;i>=0;--i){
                n.a[i]^=f.mul(amplitude,value);
                value=d.a[i]^f.mul(root,value);
            }
            require(value==0,"synthetic root division");
        }
        n.trim();
    }
    void active(const ErrorWord& e,Poly n,Poly d,Result& out) const {
        for(int index=0;index<e.weight;++index){
            const auto nr=remainder(n,index),dr=remainder(d,index);
            const bool nz=nr[0]==0&&nr[1]==0,dz=dr[0]==0&&dr[1]==0;
            if(nz||dz){
                require(!(nz&&dz),"coprime active pair vanished twice");
                out.finite_slot=index;out.finite_kind=nz?FINITE_N:FINITE_D;
                out.reason|=out.finite_kind;out.nrem=nr;out.drem=dr;return;
            }
            const auto head=qdiv(dr,nr,index);
            Poly r=d;r.size=std::max(d.size,n.size+1);
            for(int k=0;k<n.size;++k){r.a[k]^=f.mul(head[0],n.a[k]);r.a[k+1]^=f.mul(head[1],n.a[k]);}
            r.trim();Poly next;next.size=std::max(0,r.size-2);
            for(int k=r.size-1;k>=2;--k){
                const Word v=r.a[k];next.a[k-2]=v;r.a[k]=0;r.a[k-1]^=v;r.a[k-2]^=constant_mul[index][v];
            }
            require(r.a[0]==0&&r.a[1]==0,"active quadratic division remainder");
            next.trim();d=n;n=next;
            require(n.size<=e.weight-index-1&&d.size<=e.weight-index,"active degree bound");
        }
        require(n.size==0&&d.size==1&&d.a[0]!=0,"active terminal");
    }
    HalfProfile half(const Poly& d) const {
        require(d.size==36&&d.a[35]!=0,"full35 source");
        std::array<Word,18> a{},b{};
        for(int i=0;i<18;++i)a[i]=f.root[d.a[2*i+1]];
        const Word q=f.div(f.root[d.a[34]],a[17]);
        for(int i=0;i<17;++i)b[i]=f.root[d.a[2*i]]^f.mul(q,a[i]);
        int da=17,db=16;while(db>=0&&b[db]==0)--db;
        HalfProfile result;result.mask=1u<<17;result.degrees[result.count++]=17;
        while(db>=0){
            const int drop=da-db;
            if(drop>2)result.reason|=DROP;
            if(drop==2)result.drop2|=1u<<da;
            result.mask|=1u<<db;result.degrees[result.count++]=db;
            const Word reciprocal=f.inverse[b[db]];
            for(int i=da;i>=db;--i)if(a[i]){
                const Word factor=f.mul(a[i],reciprocal);a[i]=0;
                for(int k=0;k<db;++k)a[i-db+k]^=f.mul(factor,b[k]);
            }
            std::swap(a,b);da=db;db=da-1;while(db>=0&&b[db]==0)--db;
        }
        if(da!=0){result.reason|=GCD;result.mask|=1u<<30;}
        if((result.drop2&((1u<<17)|(1u<<15)))==((1u<<17)|(1u<<15)))result.reason|=WINDOW17;
        if((result.drop2&((1u<<14)|(1u<<12)))==((1u<<14)|(1u<<12)))result.reason|=WINDOW14;
        return result;
    }
    Result classify(const ErrorWord& e) const {
        Result out;out.weight=e.weight;Poly n,d;physical_pair(e,n,d);
        out.full=polynomial_product(f,d,padding[e.weight]);
        require(out.full.size==36&&out.full.a[35]==1,"padded degree35");
        out.half=half(out.full);out.reason=out.half.reason;active(e,n,d,out);return out;
    }
};

struct Config {
    std::string digest;
    U64 planned_draws=0,seed=0;
    std::array<U64,35> upper{};
    std::array<Word,35> kappas{};
};
static Config read_config(const std::string& path,const Classifier& classifier) {
    std::ifstream in(path);require(bool(in),"configuration open");
    std::string magic;Config c;int modulus=0,kappa=0;
    in>>magic>>c.digest>>c.planned_draws>>c.seed>>modulus>>kappa;
    require(magic=="DQI_C27_CONFIG_V1"&&c.digest.size()==64,"configuration ABI");
    require(c.planned_draws==500000000&&c.seed==202611112245ULL,"fixed plan mismatch");
    require(modulus==0x1053&&kappa==2048,"field configuration");
    for(auto& x:c.upper)in>>x;
    for(auto& x:c.kappas)in>>x;
    require(bool(in)&&std::is_sorted(c.upper.begin(),c.upper.end()),"configuration thresholds");
    require(c.kappas==classifier.kappas,"configuration nodes");
    return c;
}

struct Witness {U64 draw=0;ErrorWord error;int reason=0;std::uint32_t profile=0;};
struct State {
    std::string mode;
    U64 seed=0,draws=0;
    std::mt19937_64 random;
    std::array<std::array<U64,64>,36> reasons{};
    std::array<std::array<U64,35>,36> nslots{},dslots{};
    std::map<std::pair<int,std::uint32_t>,U64> profiles;
    std::vector<Witness> witnesses;
};
static void validate_state(const State& s) {
    U64 reasons=0,profiles=0,n=0,d=0,nslots=0,dslots=0;
    for(int j=0;j<36;++j){
        for(int mask=0;mask<64;++mask){reasons+=s.reasons[j][mask];if(mask&FINITE_N)n+=s.reasons[j][mask];if(mask&FINITE_D)d+=s.reasons[j][mask];}
        for(int i=0;i<35;++i){nslots+=s.nslots[j][i];dslots+=s.dslots[j][i];}
    }
    for(const auto& item:s.profiles)profiles+=item.second;
    require(reasons==s.draws&&profiles==s.draws&&n==nslots&&d==dslots,"state counter sums");
    require(s.witnesses.size()<=64,"state witness capacity");
}
static bool read_state(const std::string& path,const Config& c,State& s) {
    std::ifstream in(path);if(!in)return false;
    std::string magic,digest;in>>magic>>digest>>s.mode>>s.seed>>s.draws>>s.random;
    require(magic=="DQI_C27_STATE_V1"&&digest==c.digest,"state/configuration mismatch");
    for(auto& row:s.reasons)for(auto& v:row)in>>v;
    for(auto& row:s.nslots)for(auto& v:row)in>>v;
    for(auto& row:s.dslots)for(auto& v:row)in>>v;
    std::size_t count=0;in>>count;
    for(std::size_t k=0;k<count;++k){int j;std::uint32_t mask;U64 n;in>>j>>mask>>n;require(j>=0&&j<=35,"state weight");s.profiles[{j,mask}]=n;}
    in>>count;require(count<=64,"state witness count");
    for(std::size_t k=0;k<count;++k){Witness w;in>>w.draw>>w.error.weight>>w.reason>>w.profile;require(w.error.weight>=0&&w.error.weight<=35,"witness weight");for(int i=0;i<w.error.weight;++i)in>>w.error.roots[i]>>w.error.values[i];s.witnesses.push_back(w);}
    require(bool(in),"truncated state");validate_state(s);return true;
}
static void save_state(const std::string& path,const Config& c,const State& s) {
    validate_state(s);const std::string temp=path+".tmp";
    {
        std::ofstream out(temp);require(bool(out),"state temporary open");
        out<<"DQI_C27_STATE_V1\n"<<c.digest<<'\n'<<s.mode<<' '<<s.seed<<' '<<s.draws<<'\n'<<s.random<<'\n';
        for(const auto& row:s.reasons){for(auto v:row)out<<v<<' ';out<<'\n';}
        for(const auto& row:s.nslots){for(auto v:row)out<<v<<' ';out<<'\n';}
        for(const auto& row:s.dslots){for(auto v:row)out<<v<<' ';out<<'\n';}
        out<<s.profiles.size()<<'\n';for(const auto& item:s.profiles)out<<item.first.first<<' '<<item.first.second<<' '<<item.second<<'\n';
        out<<s.witnesses.size()<<'\n';
        for(const auto& w:s.witnesses){out<<w.draw<<' '<<w.error.weight<<' '<<w.reason<<' '<<w.profile;for(int i=0;i<w.error.weight;++i)out<<' '<<w.error.roots[i]<<' '<<w.error.values[i];out<<'\n';}
        out.flush();require(bool(out),"state write");
    }
    require(std::rename(temp.c_str(),path.c_str())==0,"atomic state rename");
}
static U64 bounded(State& s,U64 bound) {
    const U64 threshold=-bound%bound;
    for(;;){const U64 v=s.random();if(v>=threshold)return v%bound;}
}
static ErrorWord draw(State& s,const Config& c,std::array<U64,4096>& seen) {
    ErrorWord e;const U64 u=s.random();e.weight=int(std::upper_bound(c.upper.begin(),c.upper.end(),u)-c.upper.begin());
    const U64 tag=s.draws+1;
    for(int i=0;i<e.weight;++i){Word a;do{a=Word(1+bounded(s,4095));}while(seen[a]==tag);seen[a]=tag;e.roots[i]=a;}
    for(int i=0;i<e.weight;++i)e.values[i]=Word(1+bounded(s,4095));
    return e;
}
static U64 union_count(const State& s,int cutoff) {
    U64 out=0;for(int j=0;j<36;++j)for(int mask=0;mask<64;++mask)if(j<cutoff||mask)out+=s.reasons[j][mask];return out;
}
static void output_result(std::ostream& out,const Result& r,bool polynomial=false) {
    out<<"{\"weight\":"<<r.weight<<",\"reason_mask\":"<<r.reason<<",\"finite\":{\"bad\":"<<(r.finite_kind?"true":"false")<<",\"slot\":"<<r.finite_slot<<",\"kind\":";
    if(r.finite_kind)out<<'"'<<(r.finite_kind==FINITE_N?"N":"D")<<'"';else out<<"null";
    if(r.finite_kind)out<<",\"numerator_remainder\":["<<r.nrem[0]<<','<<r.nrem[1]<<"],\"denominator_remainder\":["<<r.drem[0]<<','<<r.drem[1]<<']';
    out<<"},\"half\":{\"degree_mask\":"<<r.half.mask<<",\"reason_mask\":"<<r.half.reason<<",\"admitted\":"<<(r.half.reason?"false":"true")<<",\"degrees\":[";
    for(int i=0;i<r.half.count;++i)out<<(i?",":"")<<r.half.degrees[i];
    out<<"],\"drop2_starts\":[";bool comma=false;
    for(int i=17;i>0;--i)if(r.half.drop2&(1u<<i)){out<<(comma?",":"")<<i;comma=true;}
    out<<"]},\"union\":{";
    for(int k=15;k<=17;++k)out<<(k==15?"":",")<<'"'<<k<<"\":"<<((r.weight<k||r.reason)?"true":"false");
    out<<'}';
    if(polynomial){out<<",\"padded_locator\":[";for(int i=0;i<r.full.size;++i)out<<(i?",":"")<<r.full.a[i];out<<']';}
    out<<'}';
}

int main(int argc,char** argv) try {
    std::map<std::string,std::string> args;
    require((argc-1)%2==0,"arguments require key/value pairs");
    for(int i=1;i<argc;i+=2){require(args.emplace(argv[i],argv[i+1]).second,"duplicate argument");}
    auto get=[&](const std::string& key,const std::string& fallback=""){const auto p=args.find(key);return p==args.end()?fallback:p->second;};
    const Classifier classifier;
    if(!get("--cases").empty()){
        std::ifstream in(get("--cases"));require(bool(in),"cases open");U64 index=0;ErrorWord e;
        while(in>>e.weight){require(e.weight>=0&&e.weight<=35,"case weight");for(int i=0;i<e.weight;++i)in>>e.roots[i]>>e.values[i];require(bool(in),"truncated case");
            std::cout<<"{\"case\":"<<++index<<",\"classification\":";output_result(std::cout,classifier.classify(e),true);std::cout<<"}\n";}
        require(in.eof(),"cases parse");return 0;
    }
    if(!get("--denominators").empty()){
        std::ifstream in(get("--denominators"));require(bool(in),"denominators open");U64 index=0;int length=0;
        while(in>>length){require(length==36,"denominator length");Result r;r.full.size=36;
            for(int i=0;i<36;++i)in>>r.full.a[i];
            require(bool(in),"truncated denominator");
            r.half=classifier.half(r.full);r.reason=r.half.reason;
            std::cout<<"{\"case\":"<<++index<<",\"classification\":";output_result(std::cout,r,true);std::cout<<"}\n";}
        require(in.eof(),"denominators parse");return 0;
    }
    const Config config=read_config(get("--config"),classifier);
    const std::string mode=get("--mode","validation"),path=get("--state");
    require(mode=="validation"||mode=="production","mode");require(!path.empty(),"state path required");
    const U64 seed=std::stoull(get("--seed",mode=="production"?"202611112245":"202611111515"));
    require((mode=="production")==(seed==config.seed),"production/validation seed separation");
    State state;
    if(!read_state(path,config,state)){state.mode=mode;state.seed=seed;state.random.seed(seed);}
    else require(state.mode==mode&&state.seed==seed,"resume mode or seed mismatch");
    const U64 additional=std::stoull(get("--draws","0"));
    require(additional<=UINT64_MAX-state.draws,"draw overflow");const U64 end=state.draws+additional;
    require(mode!="production"||end<=config.planned_draws,"fixed production N exceeded");
    const U64 interval=std::stoull(get("--save-every","100000"));require(interval>0,"save interval");
    const U64 audit_limit=std::stoull(get("--audit-limit","0"));std::ofstream audit;
    if(!get("--audit").empty()){audit.open(get("--audit"),std::ios::app);require(bool(audit),"audit open");}
    std::array<U64,4096> seen{};std::signal(SIGTERM,stop_handler);std::signal(SIGINT,stop_handler);
    const U64 before=state.draws;const auto started=std::chrono::steady_clock::now();
    while(state.draws<end&&!stopping){
        const auto error=draw(state,config,seen);const auto result=classifier.classify(error);++state.draws;
        ++state.reasons[error.weight][result.reason];++state.profiles[{error.weight,result.half.mask}];
        if(result.finite_kind==FINITE_N)++state.nslots[error.weight][result.finite_slot];
        if(result.finite_kind==FINITE_D)++state.dslots[error.weight][result.finite_slot];
        if((error.weight<17||result.reason)&&state.witnesses.size()<64)state.witnesses.push_back({state.draws,error,result.reason,result.half.mask});
        if(audit.is_open()&&state.draws<=audit_limit){
            audit<<"{\"draw\":"<<state.draws<<",\"roots\":[";for(int i=0;i<error.weight;++i)audit<<(i?",":"")<<error.roots[i];
            audit<<"],\"values\":[";for(int i=0;i<error.weight;++i)audit<<(i?",":"")<<error.values[i];audit<<"],\"classification\":";output_result(audit,result);audit<<"}\n";
        }
        if(state.draws%interval==0)save_state(path,config,state);
    }
    save_state(path,config,state);
    const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    const bool completed=mode=="production"&&state.draws==config.planned_draws;
    std::cout<<"{\"status\":\""<<(stopping?"STOPPED_AND_SAVED":completed?"FIXED_N_COMPLETE_COUNTS_ONLY":"INCOMPLETE_OR_VALIDATION_COUNTS_ONLY")
        <<"\",\"mode\":\""<<mode<<"\",\"draws\":"<<state.draws<<",\"additional_draws\":"<<state.draws-before
        <<",\"planned_draws\":"<<config.planned_draws<<",\"union15\":"<<union_count(state,15)<<",\"union16\":"<<union_count(state,16)
        <<",\"union17\":"<<union_count(state,17)<<",\"profile_bins\":"<<state.profiles.size()<<",\"witnesses\":"<<state.witnesses.size()
        <<",\"seconds\":"<<seconds<<",\"claim\":\"classical event counts only; no quantum or official verifier result\"}\n";
    return stopping?75:0;
} catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
